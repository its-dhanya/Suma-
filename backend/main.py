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

from record import record_audio, capture_screen, stop_flag, AUDIO_FS

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve session files statically (for downloads/viewing)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR, exist_ok=True)
app.mount("/sessions", StaticFiles(directory=SESSIONS_DIR), name="sessions")

# Logging setup
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "main.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Thread handles & job store
audio_thread = None
screen_thread = None
jobs: dict[str, dict] = {}  # jobId -> {"status": "pending/done/error", "result": {...}}

# Global variable to hold the current session directory
CURRENT_SESSION_DIR = None

@app.post("/start-session")
def start_session():
    global audio_thread, screen_thread, CURRENT_SESSION_DIR
    stop_flag.clear()
    # Create a new session directory for each recording session.
    timestamp = datetime.now().strftime("session_%Y%m%d_%H%M%S")
    CURRENT_SESSION_DIR = os.path.join(SESSIONS_DIR, timestamp)
    try:
        os.makedirs(CURRENT_SESSION_DIR, exist_ok=True)
        logging.info(f"Session directory created at: {CURRENT_SESSION_DIR}")
    except Exception as e:
        logging.error(f"Failed to create session directory: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session directory")
    # Define the audio file path based on the new session directory.
    audio_file = os.path.join(CURRENT_SESSION_DIR, "audio.wav")
    
    audio_thread = threading.Thread(target=record_audio, args=(audio_file,), name="AudioThread")
    screen_thread = threading.Thread(target=capture_screen, args=(CURRENT_SESSION_DIR,), name="ScreenThread")
    audio_thread.start()
    screen_thread.start()
    logging.info("▶️ Recording session started")
    return {"message": "Session started", "session_folder": os.path.basename(CURRENT_SESSION_DIR)}

@app.post("/stop-session")
def stop_session():
    global audio_thread, screen_thread
    if not audio_thread or not screen_thread:
        raise HTTPException(status_code=400, detail="No session in progress")
    stop_flag.set()
    logging.info("⏹️ Stop signal sent")
    return {"message": "Stopping session"}

@app.get("/session-status")
def session_status():
    return {
        "audio_alive": audio_thread.is_alive() if audio_thread else False,
        "screen_alive": screen_thread.is_alive() if screen_thread else False,
    }

def find_latest_session():
    # If a current session exists, use it; otherwise, find the latest session directory in SESSIONS_DIR.
    global CURRENT_SESSION_DIR
    if CURRENT_SESSION_DIR and os.path.exists(CURRENT_SESSION_DIR):
        return CURRENT_SESSION_DIR
    sessions = sorted(os.listdir(SESSIONS_DIR))
    if not sessions:
        raise HTTPException(status_code=404, detail="No sessions found")
    return os.path.join(SESSIONS_DIR, sessions[-1])

@app.post("/transcribe")
def transcribe_session():
    session = find_latest_session()
    audio_path = os.path.join(session, "audio.wav")
    from transcribe import transcribe  # import here so that transcribe is only needed when used
    text = transcribe(audio_path)
    out_path = os.path.join(session, "transcript.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    logging.info("✅ Transcription done (%d characters)", len(text))
    return {"transcript": text, "session_folder": os.path.basename(session)}

@app.post("/ocr")
def ocr_session():
    session = find_latest_session()
    results = []
    from ocr import ocr_image  # import here
    for fname in sorted(os.listdir(session)):
        if fname.endswith(".png"):
            path = os.path.join(session, fname)
            text = ocr_image(path)
            results.append({fname: text})
            with open(os.path.join(session, f"ocr_{fname}.txt"), "w", encoding="utf-8") as of:
                of.write(text)
    logging.info("✅ OCR done (%d images)", len(results))
    return {"ocr_results": results, "session_folder": os.path.basename(session)}

@app.get("/youtube-transcript")
def youtube_transcript(videoURL: str = Query(..., alias="videoURL")):
    """
    Fetches the transcript for a given YouTube video URL.
    Saves the transcript into the current session folder.
    """
    if not videoURL:
        raise HTTPException(status_code=400, detail="Missing YouTube video URL")
    try:
        # Use urllib.parse to extract the video ID from the URL reliably.
        parsed_url = urlparse(videoURL)
        query_params = parse_qs(parsed_url.query)
        video_ids = query_params.get("v")
        if not video_ids:
            raise HTTPException(status_code=400, detail="Invalid YouTube video URL; missing 'v' parameter.")
        video_id = video_ids[0]

        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        full_transcript = "\n".join(segment["text"] for segment in transcript_data)
        logging.info("✅ YouTube transcript retrieved for video_id %s", video_id)

        # Use the CURRENT_SESSION_DIR if available, otherwise use the latest session.
        session = CURRENT_SESSION_DIR if CURRENT_SESSION_DIR else find_latest_session()
        if not os.path.exists(session):
            logging.error("Session directory '%s' does not exist.", session)
            os.makedirs(session, exist_ok=True)
            logging.info("Session directory '%s' created.", session)

        transcript_path = os.path.join(session, "transcript.txt")
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(full_transcript)
        logging.info("✅ Transcript saved to %s", transcript_path)

        return {"transcript": full_transcript}
    except (TranscriptsDisabled, NoTranscriptFound):
        raise HTTPException(status_code=404, detail="Transcript not available for this video.")
    except Exception as e:
        logging.exception("Failed to process YouTube transcript for URL: %s", videoURL)
        raise HTTPException(status_code=500, detail="Failed to process transcript.") from e

@app.post("/summarize")
def start_summarization(request: Request):
    session = find_latest_session()
    transcript_file = os.path.join(session, "transcript.txt")
    from transcribe import transcribe  # in case transcription is needed
    if os.path.exists(transcript_file):
        with open(transcript_file, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        audio_path = os.path.join(session, "audio.wav")
        text = transcribe(audio_path)
    
    # Load OCR texts
    ocr_texts = []
    for fname in sorted(os.listdir(session)):
        if fname.startswith("ocr_") and fname.endswith(".txt"):
            with open(os.path.join(session, fname), "r", encoding="utf-8") as of:
                ocr_texts.append(of.read())
    
    combined = text + "\n\n" + "\n\n".join(ocr_texts)
    logging.info("Starting summarization job for session '%s', %d characters", session, len(combined))
    
    job_id = uuid4().hex
    jobs[job_id] = {"status": "pending", "result": None}

    def worker():
        try:
            from summarize import summarize  # import here to perform summarization
            structured = summarize(combined)
            out_json = os.path.join(session, "summary.json")
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(structured, f, ensure_ascii=False, indent=2)
            jobs[job_id].update(status="done", result=structured)
            logging.info("✅ Summarization job %s done", job_id)
        except Exception as e:
            jobs[job_id].update(status="error", result=str(e))
            logging.exception("Summarization job %s failed", job_id)
    
    threading.Thread(target=worker, daemon=True).start()
    return {"jobId": job_id}

@app.get("/summary/{job_id}")
def get_summary(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)