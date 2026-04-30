"""
record.py — Audio recording + visual capture module.

Supports two capture modes (set via ENV or at runtime):
  - "esp32"  : Pull JPEG frames from an ESP32-CAM HTTP stream (production)
  - "screen" : Grab the primary monitor with mss (fallback / dev mode)

Set CAPTURE_MODE=esp32  and  ESP32_CAM_URL=http://<IP>/capture  in your .env
to use the real hardware. Leave CAPTURE_MODE=screen for local dev / testing.
"""

import os
import io
import time
import threading
import logging
import wave
import signal
from datetime import datetime

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
SCREENSHOT_INTERVAL = int(os.getenv("SCREENSHOT_INTERVAL", 5))
CAPTURE_MODE        = os.getenv("CAPTURE_MODE", "screen").lower()   # "esp32" | "screen"
ESP32_CAM_URL       = os.getenv("ESP32_CAM_URL", "http://192.168.4.1/capture")
ESP32_STREAM_URL    = os.getenv("ESP32_STREAM_URL", "http://192.168.4.1:81/stream")
ESP32_TIMEOUT       = int(os.getenv("ESP32_TIMEOUT", 5))            # seconds per frame request

AUDIO_FS = 44100

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "record.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ── Shared stop flag ───────────────────────────────────────────────────────────
stop_flag = threading.Event()


def signal_handler(sig, frame):
    logging.info("Termination signal received — stopping session")
    stop_flag.set()


signal.signal(signal.SIGINT, signal_handler)


# ══════════════════════════════════════════════════════════════════════════════
# AUDIO RECORDING
# ══════════════════════════════════════════════════════════════════════════════

def record_audio(output_file: str, samplerate: int = AUDIO_FS) -> None:
    """
    Record from the default microphone (or INMP441 via I2S bridge) until
    stop_flag is set, then write a WAV file.
    """
    logging.info(f"Audio recording started → {output_file}")
    channels = 1
    frames   = []

    try:
        with sd.InputStream(samplerate=samplerate, channels=channels, dtype="int16") as stream:
            while not stop_flag.is_set():
                data, overflow = stream.read(samplerate // 5)
                if overflow:
                    logging.warning("Audio buffer overflow")
                frames.append(data.copy())

        if not frames:
            logging.error("No audio frames captured")
            return

        audio = np.concatenate(frames, axis=0)
        with wave.open(output_file, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(samplerate)
            wf.writeframes(audio.tobytes())

        logging.info(f"Audio saved: {output_file} ({len(frames)} chunks)")

    except Exception:
        logging.exception("Audio recording failed")


# ══════════════════════════════════════════════════════════════════════════════
# ESP32-CAM CAPTURE
# ══════════════════════════════════════════════════════════════════════════════

def _save_jpeg_bytes(jpeg_bytes: bytes, path: str) -> None:
    """Write raw JPEG bytes to disk."""
    with open(path, "wb") as f:
        f.write(jpeg_bytes)


def _fetch_esp32_still(session_dir: str) -> None:
    """
    Poll the ESP32-CAM /capture endpoint once per SCREENSHOT_INTERVAL seconds.
    Each response is a JPEG; we save it as a PNG-named file for pipeline
    compatibility (Pillow / OpenCV open either format transparently).
    """
    import requests  # lazy import — only needed in esp32 mode

    count = 0
    logging.info(f"ESP32-CAM still-capture started (URL: {ESP32_CAM_URL})")

    while not stop_flag.is_set():
        try:
            resp = requests.get(ESP32_CAM_URL, timeout=ESP32_TIMEOUT, stream=False)
            resp.raise_for_status()

            filename = os.path.join(session_dir, f"screenshot_{count:03}.png")
            _save_jpeg_bytes(resp.content, filename)
            logging.info(f"ESP32 frame saved: {filename}")
            count += 1

        except Exception as e:
            logging.warning(f"ESP32 frame fetch failed: {e}")

        time.sleep(SCREENSHOT_INTERVAL)

    logging.info("ESP32-CAM still-capture stopped")


def _fetch_esp32_stream(session_dir: str) -> None:
    """
    Read from the ESP32-CAM MJPEG stream endpoint (:81/stream).
    Parses multipart/x-mixed-replace boundaries to extract individual JPEGs.
    Falls back to the still-capture method on error.
    """
    import requests

    count = 0
    logging.info(f"ESP32-CAM MJPEG stream started (URL: {ESP32_STREAM_URL})")
    last_saved = time.time()

    try:
        with requests.get(ESP32_STREAM_URL, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            buffer = b""
            for chunk in resp.iter_content(chunk_size=4096):
                if stop_flag.is_set():
                    break
                buffer += chunk
                # JPEG SOI/EOI markers
                start = buffer.find(b"\xff\xd8")
                end   = buffer.find(b"\xff\xd9")
                if start != -1 and end != -1 and end > start:
                    jpeg_bytes = buffer[start: end + 2]
                    buffer = buffer[end + 2:]
                    now = time.time()
                    if now - last_saved >= SCREENSHOT_INTERVAL:
                        filename = os.path.join(session_dir, f"screenshot_{count:03}.png")
                        _save_jpeg_bytes(jpeg_bytes, filename)
                        logging.info(f"MJPEG frame saved: {filename}")
                        count += 1
                        last_saved = now

    except Exception as e:
        logging.warning(f"MJPEG stream failed ({e}), falling back to still capture")
        _fetch_esp32_still(session_dir)

    logging.info("ESP32-CAM MJPEG stream stopped")


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN CAPTURE (fallback / dev mode)
# ══════════════════════════════════════════════════════════════════════════════

def _capture_screen(session_dir: str) -> None:
    """Capture the primary monitor with mss every SCREENSHOT_INTERVAL seconds."""
    import mss
    import mss.tools

    logging.info("Screen-capture mode started")
    count = 0

    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            while not stop_flag.is_set():
                filename = os.path.join(session_dir, f"screenshot_{count:03}.png")
                img = sct.grab(monitor)
                mss.tools.to_png(img.rgb, img.size, output=filename)
                logging.info(f"Screenshot saved: {filename}")
                count += 1
                time.sleep(SCREENSHOT_INTERVAL)
    except Exception:
        logging.exception("Screen capture failed")


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

def capture_screen(session_dir: str) -> None:
    """
    Entry point for the capture thread.
    Routes to ESP32-CAM (MJPEG stream or still poll) or screen capture
    based on the CAPTURE_MODE environment variable.
    """
    if CAPTURE_MODE == "esp32":
        # Prefer MJPEG streaming; _fetch_esp32_stream falls back to still if needed
        _fetch_esp32_stream(session_dir)
    else:
        _capture_screen(session_dir)


def get_capture_mode() -> str:
    """Return the active capture mode string for status reporting."""
    return CAPTURE_MODE