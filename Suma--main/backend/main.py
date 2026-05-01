"""
main.py — FastAPI back-end for the AI Multimodal Classroom Note-Taking System.

Endpoints:
  POST /start-session         Start audio + visual capture
  POST /stop-session          Stop capture
  GET  /session-status        Thread liveness + capture mode
  POST /transcribe            Run Whisper ASR on session audio
  POST /ocr                   Run Tesseract OCR on captured board images
  POST /summarize             Kick off async LLM summarisation job
  GET  /summary/{job_id}      Poll summarisation job result
  GET  /av-alignment          Return timestamped audio-visual alignment
"""

import os
import threading
import logging
import json
import subprocess
import shutil
import time
from uuid import uuid4
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs

from record import record_audio, capture_screen, stop_flag, get_capture_mode

load_dotenv()

# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI(title="Classroom Note-Taking System")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
ESP32_DIR    = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "esp32"))
os.makedirs(SESSIONS_DIR, exist_ok=True)
app.mount("/sessions", StaticFiles(directory=SESSIONS_DIR), name="sessions")

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "main.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ── State ──────────────────────────────────────────────────────────────────────
audio_thread:       threading.Thread | None = None
screen_thread:      threading.Thread | None = None
guna_process:       subprocess.Popen | None = None
guna_syncing:       bool                    = False
CURRENT_SESSION_DIR: str | None             = None
jobs: dict[str, dict]                       = {}   # jobId → {status, result}


# ── Helpers ────────────────────────────────────────────────────────────────────

def find_latest_session() -> str:
    global CURRENT_SESSION_DIR
    if CURRENT_SESSION_DIR and os.path.exists(CURRENT_SESSION_DIR):
        return CURRENT_SESSION_DIR
    sessions = sorted(
        d for d in os.listdir(SESSIONS_DIR)
        if os.path.isdir(os.path.join(SESSIONS_DIR, d))
    )
    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found")
    return os.path.join(SESSIONS_DIR, sessions[-1])


# ══════════════════════════════════════════════════════════════════════════════
# SESSION MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/start-session")
def start_session(mode: str = "esp32"):
    global audio_thread, screen_thread, guna_process, guna_syncing, CURRENT_SESSION_DIR

    stop_flag.clear()
    timestamp = datetime.now().strftime("session_%Y%m%d_%H%M%S")
    CURRENT_SESSION_DIR = os.path.join(SESSIONS_DIR, timestamp)

    # Clear esp32 folder if it exists
    if os.path.exists(ESP32_DIR):
        for f in os.listdir(ESP32_DIR):
            fpath = os.path.join(ESP32_DIR, f)
            try:
                if os.path.isfile(fpath):
                    os.unlink(fpath)
            except Exception as e:
                logging.warning(f"Failed to delete {fpath}: {e}")
    else:
        os.makedirs(ESP32_DIR, exist_ok=True)

    # Start guna.py
    if mode == "esp32":
        try:
            # We assume guna.py is in the parent of the parent dir (Desktop/guna)
            guna_path = os.path.join(BASE_DIR, "..", "..", "guna.py")
            guna_process = subprocess.Popen(["python", guna_path], cwd=os.path.dirname(guna_path))
            guna_syncing = True
            logging.info("guna.py subprocess started")
        except Exception as e:
            logging.error(f"Failed to start guna.py: {e}")

    try:
        os.makedirs(CURRENT_SESSION_DIR, exist_ok=True)
        logging.info(f"Session directory created: {CURRENT_SESSION_DIR}")
    except Exception as e:
        logging.error(f"Failed to create session directory: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session directory")

    audio_file = os.path.join(CURRENT_SESSION_DIR, "audio.wav")

    audio_thread  = threading.Thread(target=record_audio,   args=(audio_file,),         name="AudioThread",  daemon=True)
    screen_thread = threading.Thread(target=capture_screen, args=(CURRENT_SESSION_DIR, mode), name="ScreenThread", daemon=True)

    audio_thread.start()
    screen_thread.start()

    logging.info("Recording session started")
    return {
        "message":       "Session started",
        "session_folder": os.path.basename(CURRENT_SESSION_DIR),
        "capture_mode":  get_capture_mode(),
    }


def delayed_stop_guna(proc: subprocess.Popen):
    global guna_syncing
    logging.info("Waiting 3 minutes before stopping guna.py...")
    time.sleep(180)
    try:
        proc.terminate()
        proc.wait(timeout=10)
        logging.info("guna.py subprocess terminated after delay")
    except Exception as e:
        logging.error(f"Error terminating guna.py: {e}")
    finally:
        guna_syncing = False

def auto_transcribe_after_stop(audio_path: str):
    """Wait for the audio thread to finish writing, then auto-transcribe."""
    if audio_thread:
        audio_thread.join(timeout=30)  # Wait up to 30s for audio to flush to disk
    if not os.path.exists(audio_path):
        logging.warning("Auto-transcribe: audio.wav not found at %s", audio_path)
        return
    try:
        logging.info("Auto-transcribe: starting transcription of %s", audio_path)
        from transcribe import transcribe
        text = transcribe(audio_path)
        logging.info("Auto-transcribe: done (%d characters)", len(text))
    except Exception as e:
        logging.exception("Auto-transcribe: failed — %s", e)


@app.post("/stop-session")
def stop_session():
    global guna_process
    if not audio_thread or not screen_thread:
        raise HTTPException(status_code=400, detail="No session in progress")
    stop_flag.set()
    logging.info("Stop signal sent")

    if guna_process:
        threading.Thread(target=delayed_stop_guna, args=(guna_process,), daemon=True).start()
        guna_process = None

    # Auto-transcribe in background once audio is saved
    if CURRENT_SESSION_DIR:
        audio_path = os.path.join(CURRENT_SESSION_DIR, "audio.wav")
        threading.Thread(
            target=auto_transcribe_after_stop,
            args=(audio_path,),
            name="AutoTranscribeThread",
            daemon=True,
        ).start()
        logging.info("Auto-transcription thread started for %s", audio_path)

    return {"message": "Stopping session. Transcription will run automatically in the background (guna.py will stop after 3 minutes)"}


@app.get("/session-status")
def session_status():
    return {
        "audio_alive":   audio_thread.is_alive()  if audio_thread  else False,
        "screen_alive":  screen_thread.is_alive() if screen_thread else False,
        "guna_syncing":  guna_syncing,
        "capture_mode":  get_capture_mode(),
        "session_folder": os.path.basename(CURRENT_SESSION_DIR) if CURRENT_SESSION_DIR else None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# TRANSCRIPTION
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/transcribe")
def transcribe_session():
    session    = find_latest_session()
    audio_path = os.path.join(session, "audio.wav")

    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="audio.wav not found in session")

    from transcribe import transcribe
    text = transcribe(audio_path)
    logging.info("Transcription done (%d characters)", len(text))
    return {"transcript": text, "session_folder": os.path.basename(session)}


# ══════════════════════════════════════════════════════════════════════════════
# OCR
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/ocr")
def ocr_session():
    session = find_latest_session()
    results = []

    # First, copy any .jpg files from esp32 folder to session folder
    if os.path.exists(ESP32_DIR):
        for fname in sorted(os.listdir(ESP32_DIR)):
            if fname.endswith(".jpg") or fname.endswith(".jpeg"):
                src = os.path.join(ESP32_DIR, fname)
                dst = os.path.join(session, fname)
                try:
                    shutil.copy2(src, dst)
                except Exception as e:
                    logging.warning(f"Failed to copy {fname} to session folder: {e}")

    from ocr import ocr_image
    for fname in sorted(os.listdir(session)):
        if (fname.endswith(".png") or fname.endswith(".jpg") or fname.endswith(".jpeg")) and not fname.startswith("ocr_"):
            path = os.path.join(session, fname)
            text = ocr_image(path)
            results.append({fname: text})
            with open(os.path.join(session, f"ocr_{fname}.txt"), "w", encoding="utf-8") as f:
                f.write(text)

    logging.info("OCR done (%d images)", len(results))
    return {"ocr_results": results, "session_folder": os.path.basename(session)}


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARISATION (async job)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/summarize")
def start_summarization(request: Request):
    session = find_latest_session()

    # ── 1. Load audio transcript (plain text) ─────────────────────────
    transcript_file = os.path.join(session, "transcript.txt")
    if os.path.exists(transcript_file):
        with open(transcript_file, "r", encoding="utf-8") as f:
            transcript_text = f.read()
    else:
        from transcribe import transcribe
        audio_path = os.path.join(session, "audio.wav")
        if not os.path.exists(audio_path):
            raise HTTPException(status_code=404, detail="No transcript or audio found in session")
        transcript_text = transcribe(audio_path)

    # ── 2. Load timed segments for timestamp alignment ─────────────────
    from transcribe import get_timed_segments
    timed_segments = get_timed_segments(session)

    # ── 3. Load OCR texts (one per captured image), labeled by filename ─
    ocr_texts  = []
    ocr_by_img = {}   # maps image filename → ocr text
    for fname in sorted(os.listdir(session)):
        if fname.startswith("ocr_") and fname.endswith(".txt"):
            with open(os.path.join(session, fname), "r", encoding="utf-8") as f:
                content = f.read().strip()
            ocr_texts.append(content)
            # Derive the image filename from "ocr_<imgname>.txt"
            img_name = fname[len("ocr_"):-len(".txt")]
            ocr_by_img[img_name] = content

    # ── 4. Copy esp32 images to session folder (in case not copied yet) ─
    if os.path.exists(ESP32_DIR):
        for fname in sorted(os.listdir(ESP32_DIR)):
            if fname.endswith(".jpg") or fname.endswith(".jpeg"):
                src = os.path.join(ESP32_DIR, fname)
                dst = os.path.join(session, fname)
                try:
                    shutil.copy2(src, dst)
                except Exception:
                    pass

    # ── 5. Build alignment list enriched with OCR text ────────────────
    screenshot_interval = int(os.getenv("SCREENSHOT_INTERVAL", 5))
    screenshots = sorted(
        f for f in os.listdir(session)
        if (f.startswith("screenshot_") and f.endswith(".png"))
        or (f.startswith("image_") and f.endswith(".jpg"))
    )
    try:
        session_start = datetime.strptime(
            os.path.basename(session), "session_%Y%m%d_%H%M%S"
        ).timestamp()
    except Exception:
        session_start = time.time()

    alignment = []
    for idx, fname in enumerate(screenshots):
        if fname.startswith("image_"):
            try:
                epoch_str = fname.replace("image_", "").replace(".jpg", "")
                cap_start = max(0, int(epoch_str) - session_start)
                cap_end   = cap_start + screenshot_interval
            except Exception:
                cap_start = idx * screenshot_interval
                cap_end   = cap_start + screenshot_interval
        else:
            cap_start = idx * screenshot_interval
            cap_end   = cap_start + screenshot_interval

        overlapping = [
            seg for seg in timed_segments
            if seg["end"] >= cap_start and seg["start"] < cap_end
        ]

        alignment.append({
            "screenshot":          fname,
            "capture_time_s":      cap_start,
            "transcript_segments": overlapping,
            "ocr_text":            ocr_by_img.get(fname, ""),
        })

    logging.info(
        "Starting summarisation job for session '%s' — transcript: %d chars, "
        "OCR images: %d, alignment entries: %d",
        session, len(transcript_text), len(ocr_texts), len(alignment)
    )

    job_id       = uuid4().hex
    jobs[job_id] = {"status": "pending", "result": None}

    def worker():
        try:
            from summarize import summarize
            structured = summarize(
                transcript_text=transcript_text,
                timed_segments=timed_segments,
                ocr_texts=ocr_texts,
                alignment=alignment,
            )
            out_json = os.path.join(session, "summary.json")
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(structured, f, ensure_ascii=False, indent=2)
            jobs[job_id].update(status="done", result=structured)
            logging.info("Summarisation job %s done", job_id)
        except Exception as e:
            jobs[job_id].update(status="error", result=str(e))
            logging.exception("Summarisation job %s failed", job_id)

    threading.Thread(target=worker, daemon=True).start()
    return {"jobId": job_id}


@app.get("/summary/{job_id}")
def get_summary(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ══════════════════════════════════════════════════════════════════════════════
# AUDIO-VISUAL TIMESTAMP ALIGNMENT
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/av-alignment")
def av_alignment():
    from transcribe import get_timed_segments

    session = find_latest_session()

    # Load timed segments
    segments = get_timed_segments(session)
    if not segments:
        raise HTTPException(
            status_code=404,
            detail="No timed transcript found. Run /transcribe first."
        )

    # First, copy any .jpg files from esp32 folder to session folder
    if os.path.exists(ESP32_DIR):
        for fname in sorted(os.listdir(ESP32_DIR)):
            if fname.endswith(".jpg") or fname.endswith(".jpeg"):
                src = os.path.join(ESP32_DIR, fname)
                dst = os.path.join(session, fname)
                try:
                    shutil.copy2(src, dst)
                except Exception as e:
                    pass

    # Collect screenshot file names
    screenshot_interval = int(os.getenv("SCREENSHOT_INTERVAL", 5))
    screenshots = sorted(
        f for f in os.listdir(session)
        if (f.startswith("screenshot_") and f.endswith(".png")) or (f.startswith("image_") and f.endswith(".jpg"))
    )

    try:
        session_start = datetime.strptime(os.path.basename(session), "session_%Y%m%d_%H%M%S").timestamp()
    except:
        session_start = time.time()

    # Build alignment
    alignment = []
    for idx, fname in enumerate(screenshots):
        if fname.startswith("image_"):
            try:
                epoch_str = fname.replace("image_", "").replace(".jpg", "")
                cap_start = max(0, int(epoch_str) - session_start)
                cap_end = cap_start + screenshot_interval
            except:
                cap_start = idx * screenshot_interval
                cap_end = cap_start + screenshot_interval
        else:
            cap_start = idx * screenshot_interval
            cap_end   = cap_start + screenshot_interval

        overlapping = [
            seg for seg in segments
            if seg["end"] >= cap_start and seg["start"] < cap_end
        ]

        alignment.append({
            "screenshot":          fname,
            "capture_time_s":      cap_start,
            "transcript_segments": overlapping,
        })

    return {"session_folder": os.path.basename(session), "alignment": alignment}


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)