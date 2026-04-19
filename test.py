"""
VoicePay — test.py  (Member 2 × Member 3 Integration)
=======================================================
FULL PIPELINE:
  record.py → audio.wav → [THIS FILE] → Whisper → Groq → Flask → Result

INSTALL:
    pip install openai-whisper soundfile numpy groq requests

SET GROQ KEY (every new terminal):
    PowerShell:  $env:GROQ_API_KEY="gsk_your_key_here"

MAKE SURE Flask backend is running first:
    python app.py

RUN:
    python test.py audio.wav

OUTPUT (printed + returned as JSON):
    {"action": "send", "amount": 500, "recipient": "ali", "result": "500 rupees sent to Ali successfully"}
"""

import sys
import json
import re
import os
import getpass
import warnings
warnings.filterwarnings("ignore")

# ── Flask backend URL ─────────────────────────────────
BACKEND_URL = "http://localhost:5000/process"

# ── Groq LLM prompt ──────────────────────────────────
PROMPT = """You are the intent engine for VoicePay, a voice payment app for Pakistan.
Input is English text (translated from Urdu/Roman Urdu speech by Whisper).

Return ONLY a raw JSON object — no markdown, no explanation, nothing else.

Format:
{"action": "...", "amount": ..., "recipient": ...}

- action    → "send" | "balance" | "unknown"
- amount    → integer rupees only, or null
- recipient → lowercase first name only, or null

Rules:
- action is "send" when: send, transfer, pay, give, draw, withdraw, deposit, bhejo, de do, kar de
- action is "balance" when: balance, how much, check, batao, kitna
- recipient is the PERSON NAME receiving money — ignore: friend, brother, account, money, some, my, from, dubai

Examples:
"Send 5000 rupees to Ali"                                           → {"action":"send","amount":5000,"recipient":"ali"}
"Send some money from my account to my friend Ali which is from Dubai" → {"action":"send","amount":null,"recipient":"ali"}
"draw 50000 from my account to Ahmed"                               → {"action":"send","amount":50000,"recipient":"ahmed"}
"What is my balance"                                                → {"action":"balance","amount":null,"recipient":null}
"mere account se Aslam ko 500 bhejo"                                → {"action":"send","amount":500,"recipient":"aslam"}
"""


# ══════════════════════════════════════════════════════
#  STEP 1 — TRANSCRIBE audio.wav → English text
# ══════════════════════════════════════════════════════

def transcribe(path: str) -> str:
    if not os.path.isfile(path):
        _die(f"Audio file not found: '{path}'")

    try:
        import whisper
        import soundfile as sf
        import numpy as np
    except ImportError as e:
        _die(f"Missing dependency — run: pip install openai-whisper soundfile numpy\n  ({e})")

    try:
        audio, sr = sf.read(path, dtype="float32")

        # Convert stereo → mono
        if audio.ndim == 2:
            audio = audio.mean(axis=1)

        # Resample to 16kHz if needed (Whisper requirement)
        if sr != 16000:
            n   = int(len(audio) * 16000 / sr)
            idx = np.linspace(0, len(audio) - 1, n)
            lo  = np.floor(idx).astype(int)
            hi  = np.minimum(lo + 1, len(audio) - 1)
            frac = idx - lo
            audio = audio[lo] * (1 - frac) + audio[hi] * frac

        audio = audio.astype("float32")

        peak = float(np.max(np.abs(audio)))
        if peak < 0.005:
            _die(f"Recording is silent (peak={peak:.4f}). Re-record with record.py — speak louder!")

        model  = whisper.load_model("base")
        result = model.transcribe(audio, task="translate", fp16=False)

    except Exception as e:
        _die(f"Transcription error: {e}")

    text = result.get("text", "").strip()
    if not text:
        _die("Whisper returned empty text. Speak louder or closer to mic.")
    return text


# ══════════════════════════════════════════════════════
#  STEP 2 — EXTRACT INTENT via Groq LLM
# ══════════════════════════════════════════════════════

def extract_intent(text: str) -> dict:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        _die('GROQ_API_KEY not set.\n  PowerShell: $env:GROQ_API_KEY="gsk_your_key_here"')

    try:
        from groq import Groq
    except ImportError:
        _die("groq not installed. Run: pip install groq")

    try:
        client   = Groq(api_key=key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user",   "content": f'Voice input: "{text}"'}
            ],
            temperature=0.0,
            max_tokens=100,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```[a-z]*\s*|\s*```$", "", raw).strip()
        p   = json.loads(raw)

    except json.JSONDecodeError:
        _die(f"LLM returned non-JSON: {raw}")
    except Exception as e:
        _die(f"Groq API error: {e}")

    # Normalise fields
    action = str(p.get("action", "unknown")).lower()
    if action not in ("send", "balance", "unknown"):
        action = "unknown"

    amount_raw = p.get("amount")
    try:
        amount = int(amount_raw) if amount_raw is not None else None
    except (ValueError, TypeError):
        amount = None

    r         = p.get("recipient")
    recipient = str(r).strip().lower() if r and str(r).lower() not in ("null", "none", "") else None

    return {"action": action, "amount": amount, "recipient": recipient}


# ══════════════════════════════════════════════════════
#  STEP 3 — COLLECT sender + PIN from user
# ══════════════════════════════════════════════════════

def collect_credentials(intent: dict) -> tuple[str, str]:
    """
    Ask the user WHO they are (sender) and their PIN.
    In the Twilio integration (Member 1), sender comes from
    the registered phone number and PIN from DTMF keypad input.
    For local testing we prompt the terminal.
    """
    print("\n" + "─" * 52)
    print("  🔐  IDENTITY VERIFICATION")
    print("─" * 52)

    sender = input("  Your username (e.g. ahmed / ali): ").strip().lower()
    if not sender:
        _die("Sender name cannot be empty.")

    # Use getpass so PIN is hidden on screen (professional + secure)
    try:
        pin = getpass.getpass("  Your PIN (hidden): ").strip()
    except Exception:
        pin = input("  Your PIN: ").strip()

    if not pin:
        _die("PIN cannot be empty.")

    return sender, pin


# ══════════════════════════════════════════════════════
#  STEP 4 — SEND to Flask backend, get result
# ══════════════════════════════════════════════════════

def call_backend(payload: dict) -> str:
    try:
        import requests
    except ImportError:
        _die("requests not installed. Run: pip install requests")

    try:
        resp = requests.post(
            BACKEND_URL,
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        return resp.text.strip()

    except requests.exceptions.ConnectionError:
        _die(
            f"Cannot reach Flask backend at {BACKEND_URL}\n"
            "  → Make sure app.py is running: python app.py"
        )
    except requests.exceptions.Timeout:
        _die("Flask backend timed out (>10s). Is app.py running?")
    except Exception as e:
        _die(f"Backend error: {e}")


# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════

def _die(msg: str):
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(1)


# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        _die("Usage: python test.py audio.wav")

    audio_path = sys.argv[1]

    # ── Step 1: Transcribe ────────────────────────────
    print("\n" + "═" * 52)
    print("  🎙  VoicePay — Full Pipeline")
    print("═" * 52)
    print(f"\n  [1/4] Transcribing '{audio_path}' with Whisper...")

    transcript = transcribe(audio_path)
    print(f"\n  ✅ Transcript: \"{transcript}\"")

    # ── Step 2: Extract intent ────────────────────────
    print("\n  [2/4] Extracting intent with Groq...")
    intent = extract_intent(transcript)
    print(f"  ✅ Intent: {json.dumps(intent)}")

    # ── Step 3: Collect credentials ───────────────────
    print("\n  [3/4] Collecting credentials...")
    sender, pin = collect_credentials(intent)

    # ── Step 4: Call Flask backend ────────────────────
    print("\n  [4/4] Sending to VoicePay backend...")

    payload = {
        "action":    intent["action"],
        "sender":    sender,
        "pin":       pin,
        "recipient": intent.get("recipient"),
        "amount":    intent.get("amount"),
    }

    if intent["action"] == "unknown":
        result = "Sorry, I didn't understand that request."
    else:
        result = call_backend(payload)

    # ── Final output ──────────────────────────────────
    print("\n" + "═" * 52)
    print("  💬 RESULT:")
    print(f"  {result}")
    print("═" * 52 + "\n")

    # Also print clean JSON for Member 1 (Twilio) to consume
    output = {**intent, "sender": sender, "result": result}
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
