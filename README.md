# 📅 AgenticPhone

> ⚠️ The code is this repository is written in **June 2025**.

## Overview

**AgenticPhone** is an internet phone (VoIP) system enhanced with Large Language Models (LLMs).

Unlike traditional VoIP systems that only transmit audio, AgenticPhone **understands conversations in real time** and can take actions based on user intent, such as scheduling events.

A key challenge is that **OpenAI Whisper alone struggles with accurate Japanese transcription**, especially in noisy, real-world conversations.  
To address this, AgenticPhone integrates **few-shot prompting, self-refinement, and dialogue-level reasoning** with LLMs.

---

## 🚀 Key Features

### 📡 Client-Server VoIP Architecture
- Real-time bidirectional communication
- Server processes audio streams from both clients

### 🧠 Dialogue-Level Understanding (Core Contribution)
- The system tracks **conversation flow across multiple turns**
- Handles real-world conversational dynamics such as:
  - Changing decisions
  - Corrections
  - Cancellations

#### Example:

A: Let's meet tomorrow at 3pm  
B: Sounds good  
A: Actually, cancel that  
A: Let's do Friday instead  


→ The system correctly registers **only the final decision (Friday)**

This is a key advantage of using LLMs:
> Not just transcription, but **understanding evolving intent in bidirectional dialogue**

---

### 🎙️ Speech Recognition + Self-Refinement
- Initial transcription with Whisper
- Improved via:
  - Few-shot prompting
  - Self-refinement with LLMs

→ Converts noisy conversational speech into clean, structured text

---

### 📅 Event Extraction & Automation
- Extracts:
  - Event title
  - Date / time
  - Context
- Handles vague temporal expressions:
  - "tomorrow afternoon"
  - "next Monday"

- Automatically registers events via Google Calendar API

---

## 🔄 Pipeline


Audio (Client A/B)  
↓  
Speech-to-Text (Whisper)  
↓  
Few-shot Prompting + Self-Refinement (LLM)  
↓  
Dialogue Understanding (LLM)  
↓  
Information Extraction (LLM)  
↓  
Google Calendar API  


---

## 🧩 Tech Stack

- Speech Recognition: OpenAI Whisper
- LLM: GPT / Gemini (for refinement + reasoning)
- Audio Processing: NumPy
- Backend: Python (server-side processing)
- Integration: Google Calendar API

---

## 💡 Key Insight

Traditional pipeline:

Speech → Text → Rule-based extraction


AgenticPhone:

Speech → Text → LLM reasoning → Action


→ Enables **robust handling of real-world conversations**

---

## 🔮 Future Work

- Speaker diarization
- Fully real-time streaming pipeline
- Personalization of user preferences
- Multi-agent coordination

---

## 📌 Summary

AgenticPhone demonstrates that:

> Integrating LLMs into communication systems enables **intent-aware, action-oriented VoIP**, going beyond simple audio transmission.
