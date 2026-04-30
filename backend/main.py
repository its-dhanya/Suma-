"""
main.py — FastAPI back-end for the AI Multimodal Classroom Note-Taking System.

Endpoints:
  POST /start-session         Start audio + visual capture
  POST /stop-session          Stop capture
  GET  /session-status        Thread liveness + capture mode
  POST /transcribe            Run Whisper ASR on session audio
  POST /ocr                   Run Tesseract OCR on captured board images
  GET  /youtube-transcript    Fetch a YouTube video transcript
  POST /summarize             Kick off async LLM summarisation job
  GET  /summary/{job_id}      Poll summarisation job result
  GET  /av-alignment          Return timestamped audio-visual alignment
"""

import os
import threading
import logging
import json
from uuid import uuid4
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)

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
def start_session():
    global audio_thread, screen_thread, CURRENT_SESSION_DIR

    stop_flag.clear()
    timestamp = datetime.now().strftime("session_%Y%m%d_%H%M%S")
    CURRENT_SESSION_DIR = os.path.join(SESSIONS_DIR, timestamp)

    try:
        os.makedirs(CURRENT_SESSION_DIR, exist_ok=True)
        logging.info(f"Session directory created: {CURRENT_SESSION_DIR}")
    except Exception as e:
        logging.error(f"Failed to create session directory: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session directory")

    audio_file = os.path.join(CURRENT_SESSION_DIR, "audio.wav")

    audio_thread  = threading.Thread(target=record_audio,   args=(audio_file,),         name="AudioThread",  daemon=True)
    screen_thread = threading.Thread(target=capture_screen, args=(CURRENT_SESSION_DIR,), name="ScreenThread", daemon=True)

    audio_thread.start()
    screen_thread.start()

    logging.info("Recording session started")
    return {
        "message":       "Session started",
        "session_folder": os.path.basename(CURRENT_SESSION_DIR),
        "capture_mode":  get_capture_mode(),
    }


@app.post("/stop-session")
def stop_session():
    if not audio_thread or not screen_thread:
        raise HTTPException(status_code=400, detail="No session in progress")
    stop_flag.set()
    logging.info("Stop signal sent")
    return {"message": "Stopping session"}


@app.get("/session-status")
def session_status():
    return {
        "audio_alive":   audio_thread.is_alive()  if audio_thread  else False,
        "screen_alive":  screen_thread.is_alive() if screen_thread else False,
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

    from ocr import ocr_image
    for fname in sorted(os.listdir(session)):
        if fname.endswith(".png") and not fname.startswith("ocr_"):
            path = os.path.join(session, fname)
            text = ocr_image(path)
            results.append({fname: text})
            with open(os.path.join(session, f"ocr_{fname}.txt"), "w", encoding="utf-8") as f:
                f.write(text)

    logging.info("OCR done (%d images)", len(results))
    return {"ocr_results": results, "session_folder": os.path.basename(session)}


# ══════════════════════════════════════════════════════════════════════════════
# YOUTUBE TRANSCRIPT
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/youtube-transcript")
def youtube_transcript(videoURL: str = Query(..., alias="videoURL")):
    parsed     = urlparse(videoURL)
    video_ids  = parse_qs(parsed.query).get("v")
    if not video_ids:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL — missing 'v' parameter")

    video_id = video_ids[0]
    try:
        transcript_data  = YouTubeTranscriptApi.get_transcript(video_id)
        full_transcript  = "\n".join(seg["text"] for seg in transcript_data)
    except (TranscriptsDisabled, NoTranscriptFound):
        raise HTTPException(status_code=404, detail="Transcript not available for this video")
    except Exception as e:
        logging.exception("YouTube transcript fetch failed for %s", videoURL)
        raise HTTPException(status_code=500, detail="Failed to fetch transcript") from e

    session = CURRENT_SESSION_DIR or find_latest_session()
    os.makedirs(session, exist_ok=True)
    with open(os.path.join(session, "transcript.txt"), "w", encoding="utf-8") as f:
        f.write(full_transcript)

    logging.info("YouTube transcript saved for %s", video_id)
    return {"transcript": full_transcript}


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARISATION (async job)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/summarize")
def start_summarization(request: Request):
    session = find_latest_session()

    # Load transcript
    transcript_file = os.path.join(session, "transcript.txt")
    if os.path.exists(transcript_file):
        with open(transcript_file, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        from transcribe import transcribe
        audio_path = os.path.join(session, "audio.wav")
        if not os.path.exists(audio_path):
            raise HTTPException(status_code=404, detail="No transcript or audio found in session")
        text = transcribe(audio_path)

    # Merge OCR texts
    ocr_texts = []
    for fname in sorted(os.listdir(session)):
        if fname.startswith("ocr_") and fname.endswith(".txt"):
            with open(os.path.join(session, fname), "r", encoding="utf-8") as f:
                ocr_texts.append(f.read())

    combined = text + "\n\n" + "\n\n".join(ocr_texts)
    logging.info("Starting summarisation job for session '%s' (%d chars)", session, len(combined))

    job_id           = uuid4().hex
    jobs[job_id]     = {"status": "pending", "result": None}

    def worker():
        try:
            from summarize import summarize
            structured = summarize(combined)
            out_json   = os.path.join(session, "summary.json")
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
    """
    Align Whisper transcript segments with board screenshots by timestamp.

    Each screenshot is named screenshot_NNN.png and was captured at
      t = NNN * SCREENSHOT_INTERVAL  seconds into the session.

    Returns a list of aligned entries:
      [
        {
          "screenshot": "screenshot_000.png",
          "capture_time_s": 0,
          "transcript_segments": [
            {"start": 0.0, "end": 3.4, "text": "..."},
            ...
          ]
        },
        ...
      ]
    """
    from transcribe import get_timed_segments

    session = find_latest_session()

    # Load timed segments
    segments = get_timed_segments(session)
    if not segments:
        raise HTTPException(
            status_code=404,
            detail="No timed transcript found. Run /transcribe first."
        )

    # Collect screenshot file names + infer capture timestamps
    screenshot_interval = int(os.getenv("SCREENSHOT_INTERVAL", 5))
    screenshots = sorted(
        f for f in os.listdir(session)
        if f.startswith("screenshot_") and f.endswith(".png")
    )

    # Build alignment
    alignment = []
    for idx, fname in enumerate(screenshots):
        cap_start = idx       * screenshot_interval
        cap_end   = (idx + 1) * screenshot_interval

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