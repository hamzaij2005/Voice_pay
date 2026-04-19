"""
VoicePay — record.py
====================
Records your voice → saves as audio.wav

INSTALL (once):
    pip install sounddevice soundfile numpy

RUN:
    python record.py
"""

import sys
import os
import subprocess
import time

# ── Auto-install missing packages ────────────────────────────
for pkg in ["sounddevice", "soundfile", "numpy"]:
    try:
        __import__(pkg)
    except ImportError:
        print(f"  Installing {pkg}...")
        subprocess.run([sys.executable, "-m", "pip", "install", pkg],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

import sounddevice as sd
import soundfile   as sf
import numpy       as np

SAMPLE_RATE = 16000   # Whisper needs 16kHz
DURATION    = 6       # seconds
OUTPUT      = "audio.wav"


def main():
    print()
    print("=" * 52)
    print("         VoicePay — Voice Recorder")
    print("=" * 52)
    print()
    print("  Speak one of these when recording starts:")
    print()
    print('  ➤  "Ali ko 500 bhejo"')
    print('  ➤  "Mujhe balance batao"')
    print('  ➤  "Ahmed ko 1200 rupees send karo"')
    print()
    print(f"  Will record for {DURATION} seconds.")
    print()

    for i in [3, 2, 1]:
        print(f"  Starting in {i}...", flush=True)
        time.sleep(1)

    print()
    print("  🔴 SPEAK NOW — clearly and close to mic!")
    print()

    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32"
    )
    sd.wait()

    print("  ✅ Recording complete!")
    print()

    peak = float(np.max(np.abs(audio)))
    if peak < 0.01:
        print("  ⚠️  WARNING: Very quiet recording detected!")
        print("  Your mic may be muted. Check Windows Sound Settings → Input.")
        print()

    sf.write(OUTPUT, audio, SAMPLE_RATE, subtype="PCM_16")
    kb = os.path.getsize(OUTPUT) // 1024
    print(f"  💾 Saved:  {OUTPUT}  ({kb} KB)")
    print(f"  📊 Volume: {peak:.4f}  ← should be above 0.01")
    print()
    print("  ─────────────────────────────────────────")
    print("  Next step:  python test.py audio.wav")
    print("  ─────────────────────────────────────────")
    print()


if __name__ == "__main__":
    main()
