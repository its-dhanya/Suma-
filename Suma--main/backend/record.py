"""
record.py — Audio recording + visual capture module.

Supports capture via ESP32-CAM HTTP stream:
  - Pull JPEG frames from an ESP32-CAM HTTP stream

Set ESP32_CAM_URL=http://<IP>/capture and ESP32_STREAM_URL=http://<IP>:81/stream in your .env
to use the real hardware.
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

# ── Shared stop flag & mode ───────────────────────────────────────────────────
stop_flag = threading.Event()
_current_mode = "esp32"


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
# SCREEN CAPTURE (MSS)
# ══════════════════════════════════════════════════════════════════════════════

def _capture_screen_mss(session_dir: str) -> None:
    """
    Capture the primary monitor using mss.
    """
    import mss
    from PIL import Image

    count = 0
    logging.info("Screen capture (mss) started")

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        while not stop_flag.is_set():
            try:
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                filename = os.path.join(session_dir, f"screenshot_{count:03}.png")
                img.save(filename)
                logging.info(f"Screen frame saved: {filename}")
                count += 1
            except Exception as e:
                logging.warning(f"Screen capture failed: {e}")

            # Sleep in small increments to allow quick exit
            for _ in range(SCREENSHOT_INTERVAL * 10):
                if stop_flag.is_set():
                    break
                time.sleep(0.1)

    logging.info("Screen capture (mss) stopped")


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

def capture_screen(session_dir: str, mode: str = "esp32") -> None:
    """
    Entry point for the capture thread.
    """
    global _current_mode
    _current_mode = mode

    if mode == "screen":
        _capture_screen_mss(session_dir)
    else:
        # guna.py is handling the ESP32 stream and saving files directly.
        # We just keep this thread alive until stop_flag is set.
        while not stop_flag.is_set():
            time.sleep(1)


def get_capture_mode() -> str:
    """Return the active capture mode string for status reporting."""
    return _current_mode