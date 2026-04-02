import socket
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
import whisper
import litellm
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import google.generativeai as genai
from datetime import datetime
import os
import sys


# ========== 共通設定 ==========
GEMINI_API_KEY = "YOUR_API_KEY"
RATE = 44100
CHUNK = 512
DURATION = 20  # 通話録音秒数を10秒に変更
AUDIO_FILE = "recorded_audio.wav"
TRANSCRIPT_FILE = "transcript.txt"
MODEL = "gemini-2.5-flash"
# ==============================

def start_server(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', port))
    server.listen(1)
    print(f"[サーバー] 待機中… ポート: {port}")
    conn, addr = server.accept()
    print(f"[サーバー] 接続: {addr}")
    return conn

def start_client(ip, port):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((ip, port))
    print(f"[クライアント] 接続完了: {ip}:{port}")
    return client

def audio_communication(conn, is_server):
    """
    双方向音声ストリーミング。
    サーバー側は自分とクライアントの両方を録音し WAV に保存。
    """
    # モードに応じた開始ログ
    mode = "サーバー" if is_server else "クライアント"
    print(f"[通話開始] {mode} モードでの音声ストリーミングを開始 (録音時間: {DURATION}秒)")

    # 録音バッファ
    recorded_local = [] if is_server else None
    recorded_remote = [] if is_server else None

    # 再生ストリーム
    stream_out = sd.OutputStream(
        samplerate=RATE,
        channels=1,
        dtype='float32',
        blocksize=CHUNK,
        latency='low'
    )
    stream_out.start()

    # 受信スレッド
    stop_event = threading.Event()
    def recv_thread():
        print(f"[{mode}] 受信スレッド起動")
        try:
            while not stop_event.is_set():
                data = conn.recv(CHUNK * 4)
                if not data:
                    break
                audio = np.frombuffer(data, dtype=np.float32).reshape(-1, 1)
                stream_out.write(audio)
                if is_server:
                    recorded_remote.append(audio.copy())
        except Exception as e:
            print(f"[{mode} 受信エラー]", e)
        finally:
            stop_event.set()
            print(f"[{mode}] 受信スレッド終了")

    thread = threading.Thread(target=recv_thread, daemon=True)
    thread.start()

    # マイク送信
    def send_callback(indata, frames, time, status):
        if status:
            print(f"[{mode} 録音ステータス]", status)
        try:
            conn.sendall(indata.tobytes())
        except Exception:
            pass
        if is_server:
            recorded_local.append(indata.copy())

    with sd.InputStream(
        samplerate=RATE,
        channels=1,
        dtype='float32',
        blocksize=CHUNK,
        callback=send_callback,
        latency='low'
    ):
        sd.sleep(int(DURATION * 1000))
        stop_event.set()

    # クリーンアップ
    thread.join()
    stream_out.stop()
    stream_out.close()
    conn.close()
    print(f"[{mode}] 通話セッション終了")

    # サーバー側で録音をマージして保存
    if is_server:
        print("[サーバー] 録音ファイルをマージして保存中…")
        local = np.concatenate(recorded_local, axis=0)
        remote = np.concatenate(recorded_remote, axis=0)
        max_len = max(len(local), len(remote))
        pad_local = np.pad(local.squeeze(), (0, max_len - len(local)), 'constant')
        pad_remote = np.pad(remote.squeeze(), (0, max_len - len(remote)), 'constant')
        mixed = ((pad_local + pad_remote) / 2.0).reshape(-1, 1)
        sf.write(AUDIO_FILE, mixed, RATE)
        print("[サーバー] 録音保存完了:", AUDIO_FILE)

        # ここで次の処理に進む


def transcribe_audio():
    print("[Whisper] 書き起こし中…")
    model = whisper.load_model("base")
    result = model.transcribe(AUDIO_FILE, language = "ja")
    text = result["text"]
    with open(TRANSCRIPT_FILE, "w") as f:
        f.write(text)
    print("[Whisper] 書き起こし完了:", TRANSCRIPT_FILE)
    return text
    
def get_prompt():
    now = datetime.now()
    today_str = now.strftime("%Y年%m月%d日（%A）")  # 例: 2025年06月26日（木曜日）

    system_prompt = f"""
# あなたの役割
あなたは、会話テキストから予定を抽出するAIです。出力は厳密に予定データのみを返してください。

# 前提
- これは日常会話の書き起こしです。誤変換がある可能性があるため、文脈を読み取り正しく補完してください。
- 今日は2025年6月26日木曜日です。

# 制約
- 出力は予定のみ。説明文・解説・前置き・余談は一切含めないでください。
- 各予定は1行、以下の形式で出力してください:
  **YYYY-MM-DD HH:MM タイトル**
- 複数予定がある場合は複数行で出力してください。
- 日時は日本時間基準で、口語表現（例: 明後日、来週の火曜）は具体的な日付に変換してください。
- 今週と来週の区別を正しく行ってください。
- 予定が存在しない場合のみ「予定なし」とだけ出力してください。

# 変換例
- アサッテの県 → 明後日の件
- 習合 → 集合
- 行きまえ → 駅前

# 出力例（今日が2025年06月26日の場合）
# 例1
        - 今日の日付: 2025-06-26
        - 会話内容:
        A「次の定例会ですが、来週の月曜の朝10時でいかがでしょう？」
        B「すみません、その日は都合が悪く。翌日の火曜13時であれば可能です。」
        A「承知しました。では、来週火曜の13時に第2会議室でお願いします。」
        - 出力:
        2025-07-01 13:00 第2会議室で定例会
        
        # 例2
        - 今日の日付: 2025-06-23
        - 会話内容:
        A「明後日の件、リマインドです。15時に駅前のカフェ集合でお願いしますね。」
        B「ありがとうございます。承知しました。」
        - 出力:
        2025-06-25 15:00 駅前のカフェ集合
        
        # 例3
        - 今日の日付: 2025-06-23
        - 会話内容:
        A「最近暑いですね。また近いうちに飲みに行きましょう」
        B「いいですね, ぜひぜひ」
        - 出力:
        予定なし
"""
    return system_prompt

def extract_schedule(text):
    print("[Gemini] 予定抽出中…")

    # APIキーの設定
    if not GEMINI_API_KEY:
        raise EnvironmentError("環境変数 'GEMINI_API_KEY' が設定されていません。")
    genai.configure(api_key=GEMINI_API_KEY)

    system_prompt = get_prompt()

    # Geminiプロンプト実行
    model = genai.GenerativeModel(MODEL)
    response = model.generate_content([
        system_prompt,
        text
    ])

    result = response.text
    if not result:
        raise ValueError("[Gemini] 応答が空です")
    result = result.strip()
    print("[Gemini] 抽出結果:\n", result)
    return result


def parse_schedule_line(line):
    parts = line.strip().split(' ', 2)
    if len(parts) < 3:
        raise ValueError(f"[予定抽出] 形式エラー: {line}")
    dt = datetime.strptime(f"{parts[0]} {parts[1]}", "%Y-%m-%d %H:%M")
    title = parts[2]
    return dt, title


def add_to_calendar(text):
    print("[カレンダー] 登録処理中…")
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('calendar', 'v3', credentials=creds)

    for line in text.splitlines():
        if not line.strip():
            continue
        dt, summary = parse_schedule_line(line)
        event = {
            'summary': summary,
            'start': {'dateTime': dt.isoformat(), 'timeZone': 'Asia/Tokyo'},
            'end':   {'dateTime': (dt + timedelta(hours=1)).isoformat(), 'timeZone': 'Asia/Tokyo'}
        }
        service.events().insert(calendarId='primary', body=event).execute()
        print(f"[カレンダー] 登録完了: {summary} @ {dt}")


def main():
    try:
        argc = len(sys.argv)
        if argc == 2:
            port = int(sys.argv[1])
            conn = start_server(port)
            audio_communication(conn, True)

            text = transcribe_audio()
            extracted = extract_schedule(text)
            add_to_calendar(extracted)

        elif argc == 3:
            ip = sys.argv[1]
            port = int(sys.argv[2])
            conn = start_client(ip, port)
            audio_communication(conn, False)
        else:
            print("Usage (サーバー): python voice_schedule.py <port>")
            print("Usage (クライアント): python voice_schedule.py <server_ip> <port>")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n[終了] ユーザ中断")
    except Exception as e:
        print("[エラー発生]", e)

if __name__ == "__main__":
    main()
