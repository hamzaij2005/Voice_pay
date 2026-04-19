"""
VoicePay — debug.py
====================
Developer tool: audio.wav → Whisper → Groq → (optionally) Flask
Shows every step verbosely. Use this to diagnose issues.

INSTALL:
    pip install openai-whisper soundfile numpy groq requests

SET GROQ KEY:
    PowerShell:  $env:GROQ_API_KEY="gsk_your_key_here"

RUN (transcribe + intent only):
    python debug.py audio.wav

RUN (full pipeline including backend):
    python debug.py audio.wav --full
"""

import sys
import json
import re
import os
import warnings
warnings.filterwarnings("ignore")

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
"Send 5000 rupees to Ali" → {"action":"send","amount":5000,"recipient":"ali"}
"Send some money from my account to my friend Ali which is from Dubai" → {"action":"send","amount":null,"recipient":"ali"}
"draw 50000 from my account to Ahmed" → {"action":"send","amount":50000,"recipient":"ahmed"}
"What is my balance" → {"action":"balance","amount":null,"recipient":null}
"mere account se Aslam ko 500 bhejo" → {"action":"send","amount":500,"recipient":"aslam"}
"""

BACKEND_URL = "http://localhost:5000/process"


def transcribe(path: str) -> str:
    if not os.path.isfile(path):
        return f"ERROR: File not found - {path}"
    try:
        import whisper
        import soundfile as sf
        import numpy as np
    except ImportError as e:
        return f"ERROR: Missing dependency - {e}"
    try:
        audio, sr = sf.read(path, dtype="float32")
        if audio.ndim == 2:
            audio = audio.mean(axis=1)
        if sr != 16000:
            n = int(len(audio) * 16000 / sr)
            idx = np.linspace(0, len(audio) - 1, n)
            lo = np.floor(idx).astype(int)
            hi = np.minimum(lo + 1, len(audio) - 1)
            frac = idx - lo
            audio = audio[lo] * (1 - frac) + audio[hi] * frac
        audio = audio.astype("float32")
        model = whisper.load_model("base")
        result = model.transcribe(audio, task="translate", fp16=False)
        return result.get("text", "").strip()
    except Exception as e:
        return f"ERROR: {str(e)}"


def extract_intent(text: str) -> dict:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        return {"error": "GROQ_API_KEY not set. Run: $env:GROQ_API_KEY=\"gsk_...\""}
    try:
        from groq import Groq
        client = Groq(api_key=key)
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
        p = json.loads(raw)
    except ImportError:
        return {"error": "groq not installed. Run: pip install groq"}
    except json.JSONDecodeError:
        return {"error": f"LLM returned non-JSON: {raw}"}
    except Exception as e:
        return {"error": str(e)}

    action = str(p.get("action", "unknown")).lower()
    if action not in ("send", "balance", "unknown"):
        action = "unknown"

    amount_raw = p.get("amount")
    try:
        amount = int(amount_raw) if amount_raw is not None else None
    except (ValueError, TypeError):
        amount = None

    r = p.get("recipient")
    recipient = str(r).strip().lower() if r and str(r).lower() not in ("null", "none", "") else None

    return {"action": action, "amount": amount, "recipient": recipient}


def test_backend(intent: dict):
    """Quick backend smoke-test using hardcoded demo credentials."""
    try:
        import requests
    except ImportError:
        print("  requests not installed — skipping backend test")
        return

    # Use demo credentials for debug mode
    payload = {
        "action":    intent.get("action"),
        "sender":    "ahmed",
        "pin":       "1234",
        "recipient": intent.get("recipient"),
        "amount":    intent.get("amount"),
    }

    print("\n📡 BACKEND TEST PAYLOAD:")
    print("=" * 55)
    print(json.dumps(payload, indent=2))
    print("=" * 55)

    try:
        resp = requests.post(BACKEND_URL, json=payload, timeout=5)
        print(f"\n✅ Backend response [{resp.status_code}]:")
        print(f"   {resp.text.strip()}")
    except requests.exceptions.ConnectionError:
        print(f"\n⚠️  Backend not reachable at {BACKEND_URL}")
        print("   Start it with: python app.py")
    except Exception as e:
        print(f"\n❌ Backend error: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug.py audio.wav [--full]")
        sys.exit(1)

    full_pipeline = "--full" in sys.argv

    transcript = transcribe(sys.argv[1])

    print("\n" + "=" * 55)
    print("🔊 WHISPER TRANSCRIPTION (English always):")
    print("=" * 55)
    print(f"   '{transcript}'")
    print("=" * 55)

    if transcript.startswith("ERROR"):
        return

    intent = extract_intent(transcript)

    print("\n🎯 EXTRACTED INTENT (via Groq):")
    print("=" * 55)
    print(json.dumps(intent, indent=2, ensure_ascii=False))
    print("=" * 55 + "\n")

    if full_pipeline and "error" not in intent:
        test_backend(intent)


if __name__ == "__main__":
    main()
