# 🎙️ VoicePay

> A voice-first financial system that enables users to send money, check balance, and perform banking actions using only a phone call and natural speech — no smartphone or literacy required.

---

## 🚀 Introduction

**VoicePay** is a hackathon project built to solve real-world financial accessibility problems in developing regions.

Many users can earn and receive money but cannot use digital banking apps due to:
- Low literacy 📖
- Lack of smartphones 📱
- Complex app interfaces ❌

VoicePay removes this barrier by allowing users to interact with financial systems using **only their voice via a phone call**.

---

## 🎯 Core Idea

> “If a user can make a phone call, they can use financial services.”

---

## ⚙️ How It Works (System Overview)

---

## 🧩 System Modules

### 📞 1. Voice Interface Layer
- Handles incoming calls
- Records user voice input
- Plays AI-generated responses

**Technology:** Twilio

---

### 🧠 2. Speech & NLP Layer
- Converts speech → text
- Extracts user intent (send money, check balance, etc.)

Example:

**Technology:** Whisper + NLP

---

### ⚙️ 3. Financial Backend
- Processes transactions
- Manages wallet balances
- Handles PIN authentication
- Confirms transfers

**Technology:** Flask (Python)

---

### 🔊 4. Voice Response Layer
- Converts system response into speech
- Sends audio back via call

**Technology:** gTTS

---

## 🔐 Security Features

- 📲 Caller ID verification (Twilio)
- 🔢 4-digit PIN authentication
- ✔️ Voice confirmation (“Say YES to confirm”)

---

## 💡 Core Features (MVP)

- 💸 Send Money via voice
- 💰 Check account balance
- 🔐 Secure authentication (PIN-based)
- 📞 Fully call-based interaction system

---

## 🏗️ Architecture Style

VoicePay follows a **microservice-inspired modular design**:

- 🎙️ Voice Module (Input/Output)
- 🧠 AI/NLP Module (Understanding commands)
- ⚙️ Backend Module (Financial logic)

Each module can run and be tested independently.

---

## 🌍 Impact

VoicePay improves financial inclusion by:
- Removing literacy barriers
- Supporting basic phone users
- Making banking accessible without apps
- Enabling voice-based financial control

---

## 🏁 Final Summary

VoicePay is a **voice-first financial system** that enables users to perform banking operations through natural speech using only a phone call, eliminating the need for smartphones or literacy-based app navigation.

---