# Suma

Suma is an AI-powered classroom note-taking assistant. It records audio, captures visual context (screen or ESP32-CAM), transcribes speech, runs OCR on captured images, and generates structured lecture summaries.

## Repository

- GitHub: https://github.com/its-dhanya/Suma-

## What this repo contains

- `frontend/`: React + Vite UI
- `backend/`: FastAPI service for recording, transcription, OCR, summarization, and alignment
- `esp32/`: ESP32-CAM sketch (`esp32_cam_classroom.ino`)
- `src-tauri/` and `frontend/src-tauri/`: Tauri config/code (desktop app scaffolding)

## Tech stack

- Frontend: React 19, Vite
- Backend: FastAPI, Uvicorn
- Audio transcription: OpenAI Whisper (local)
- OCR: Tesseract + OpenCV pipeline
- Summarization: Ollama (local model, configurable)
- Capture: `mss` screen capture or ESP32-CAM stream

## Prerequisites

- Node.js 18+
- npm
- Python 3.10+
- Tesseract OCR installed on your machine (for OCR endpoint)
- Optional (for summarization): Ollama running locally

## Setup

### 1) Frontend setup

```bash
cd frontend
npm install
```

### 2) Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

## Environment variables

Backend reads environment variables from `.env` (if present).

Common variables:

- `CAPTURE_MODE` (`screen` or `esp32`, default: `screen`)
- `SCREENSHOT_INTERVAL` (seconds between captures, default: `5`)
- `ESP32_CAM_URL` (default: `http://192.168.4.1/capture`)
- `ESP32_STREAM_URL` (default: `http://192.168.4.1:81/stream`)
- `ESP32_TIMEOUT` (default: `5`)
- `WHISPER_MODEL` (default: `base`)
- `OLLAMA_URL` (default: `http://localhost:11434`)
- `OLLAMA_MODEL` (default: `phi3:mini`)

## Run the app

Open two terminals.

### Terminal A: backend

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal B: frontend

```bash
cd frontend
npm run dev
```

Frontend defaults to `http://localhost:5173` and calls backend at `http://localhost:8000`.

## API endpoints (backend)

- `POST /start-session`: start audio + visual capture
- `POST /stop-session`: stop current capture
- `GET /session-status`: session thread status + capture mode
- `POST /transcribe`: run Whisper on latest session audio
- `POST /ocr`: OCR captured images from latest session
- `GET /youtube-transcript?videoURL=...`: fetch transcript from YouTube video
- `POST /summarize`: start async summarization job
- `GET /summary/{job_id}`: poll summarization job
- `GET /av-alignment`: align timed transcript segments with screenshots

## Data output

Backend writes session artifacts under `backend/sessions/session_YYYYMMDD_HHMMSS/`, including:

- `audio.wav`
- `screenshot_*.png`
- `transcript.txt`
- `transcript_timed.json`
- `ocr_*.txt`
- `summary.json`

## ESP32 usage

For ESP32-CAM capture mode:

1. Flash `esp32/esp32_cam_classroom.ino` to your board.
2. Set `CAPTURE_MODE=esp32`.
3. Set `ESP32_CAM_URL` / `ESP32_STREAM_URL` in `.env` if needed.

If not configured, keep `CAPTURE_MODE=screen` for local development.
