"""
transcribe.py — Offline speech-to-text using OpenAI Whisper.

Returns both the full plain-text transcript AND a list of timestamped
segments so that main.py can align audio with OCR-extracted board content.
"""

import os
import json
import logging
from dotenv import load_dotenv

# Ensure ffmpeg is in PATH for Whisper
FFMPEG_DIR = r"C:\Users\dheer\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin"
if FFMPEG_DIR not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + FFMPEG_DIR

try:
    import whisper
except ImportError:
    whisper = None

load_dotenv()

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "transcribe.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Load model once at import time (avoids repeated disk I/O)
if whisper:
    logging.info(f"Loading Whisper model: {WHISPER_MODEL}")
    try:
        _model = whisper.load_model(WHISPER_MODEL)
    except Exception as e:
        logging.exception(f"Failed to load Whisper model: {e}")
        _model = None
else:
    _model = None


def transcribe(audio_path: str) -> str:
    """
    Transcribe *audio_path* and return the full plain-text transcript.

    Also writes two artefacts alongside the audio file:
      • <session>/transcript.txt       — plain text
      • <session>/transcript_timed.json — list of {start, end, text} segments
        (used by main.py for audio-visual timestamp alignment)
    """
    if _model is None:
        logging.error("Whisper model not available")
        return ""

    try:
        logging.info(f"Transcribing {audio_path}")
        result = _model.transcribe(audio_path, language="en", fp16=False)

        full_text = result.get("text", "").strip()
        segments  = result.get("segments", [])

        # ── Save plain-text transcript ─────────────────────────────────────
        txt_path = os.path.join(os.path.dirname(audio_path), "transcript.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        # ── Save timed segments for AV alignment ──────────────────────────
        timed = [
            {
                "start": round(seg.get("start", 0.0), 3),
                "end":   round(seg.get("end",   0.0), 3),
                "text":  seg.get("text", "").strip(),
            }
            for seg in segments
        ]
        timed_path = os.path.join(os.path.dirname(audio_path), "transcript_timed.json")
        with open(timed_path, "w", encoding="utf-8") as f:
            json.dump(timed, f, ensure_ascii=False, indent=2)

        logging.info(
            f"Transcript done: {len(full_text)} chars, {len(timed)} segments → "
            f"{txt_path} + {timed_path}"
        )
        return full_text

    except Exception:
        logging.exception("Transcription failed")
        return ""


def get_timed_segments(session_dir: str) -> list:
    """
    Load the timed transcript segments from *session_dir*.
    Returns a list of {start, end, text} dicts, or [] if not found.
    """
    path = os.path.join(session_dir, "transcript_timed.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logging.exception(f"Failed to load timed segments from {path}")
        return []