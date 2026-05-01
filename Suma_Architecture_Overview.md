# Suma Project Overview & Architecture

This document provides a comprehensive breakdown of the Suma application, detailing its features, setup instructions, dependency usage, and potential areas for optimization.

---

## 1. Core Features

The Suma system is an AI-powered, offline-first classroom note-taking assistant. Its primary capabilities include:

*   **Multi-modal Capture**: Records live audio via the laptop microphone while simultaneously capturing visual context (either by taking screenshots of the laptop or receiving pushed images from an ESP32-CAM over WiFi via the `guna.py` server).
*   **Offline Speech-to-Text**: Uses OpenAI Whisper to convert the recorded audio into highly accurate, timestamped text.
*   **Image OCR (Optical Character Recognition)**: Scans the captured images (like a whiteboard or presentation) and extracts the written text using deep learning models.
*   **AI Summarization**: Combines the audio transcript and the text extracted from images, sending them to a local LLM (Ollama) to generate a structured, educational summary (core concepts, examples, questions).
*   **Audio-Visual Alignment**: Syncs the transcription timestamps with the captured images so users can see exactly what was on the board when a specific sentence was spoken.
*   **YouTube Integration**: Can bypass live recording and fetch transcripts directly from YouTube videos.

---

## 2. How the System is Set Up

The application follows a standard decoupled architecture:

*   **Backend (Python / FastAPI)**: Acts as the brain. It handles the heavy lifting: recording audio, polling the ESP32 camera over WiFi, running the AI models (Whisper/OCR), and communicating with Ollama. It runs in an isolated Python virtual environment (`.venv`).
*   **Frontend (React / Vite)**: Acts as the user interface. It makes HTTP requests to the backend to start/stop sessions and display the generated summaries.
*   **System Services**: The backend relies heavily on external applications running on your machine:
    *   **Ollama**: Must be running in the background to serve the `phi3:mini` model for summarization.
    *   **Tesseract**: Must be installed on your Windows OS and added to the PATH for the fallback OCR engine to work.
*   **Hardware (ESP32-CAM)**: An external microcontroller flashed with C++ (`.ino`) code. It connects to the same WiFi network as your laptop and actively pushes images to a dedicated local Flask server (`guna.py`). The main Python backend automatically spawns this server when a session starts and gracefully shuts it down after a 3-minute delay when a session ends, ensuring all delayed photos are synced to the `esp32` folder.

---

## 3. What Each Backend Dependency is Used For

Here is a breakdown of why each library exists in your `requirements.txt`:

*   **`fastapi` & `uvicorn`**: The web framework and server. These listen for commands from the React frontend (like "Start Session" or "Summarize").
*   **`openai-whisper`**: The local AI speech-to-text model. It does not send your voice to the cloud.
*   **`easyocr` & `pytesseract`**: The two OCR engines used to extract text from images. EasyOCR uses modern AI, while Tesseract is a classic, rules-based engine.
*   **`opencv-python` (imported as `cv2`)**: A powerful image processing library. It is used to detect the corners of whiteboards, flatten the perspective, and enhance the contrast before sending the image to the OCR engines.
*   **`sounddevice` & `wave`**: Used to tap into your laptop's microphone, record the raw audio stream, and save it to your disk as a `.wav` file.
*   **`requests`**: Used to make HTTP calls. It talks to the ESP32-CAM to download images and talks to the local Ollama server to generate summaries.
*   **`youtube-transcript-api`**: Scrapes YouTube to download subtitles for a given video URL.
*   **`python-dotenv`**: Reads the configuration values (like `CAPTURE_MODE` and intervals) from the `.env` file so they aren't hardcoded in the scripts.

---

## 4. What Can Be Removed (Optimization / Debloating)

If you want to streamline the application, reduce install size, or improve performance, here are the things you can safely remove:

### 1. Remove Tesseract (Highly Recommended)
Currently, `ocr.py` processes every image *twice*: once with EasyOCR and once with Tesseract, picking whichever returns more text. 
*   **Why remove it?** EasyOCR is generally superior. Removing Tesseract means you no longer need `pytesseract` in your `requirements.txt`, nor do you need to install the Tesseract `.exe` on your Windows machine. It will also make OCR processing twice as fast.

### 2. Remove Screen Capture (`mss`) [ALREADY DONE]
This has already been removed from the current version. The system now strictly uses the ESP32-CAM for visual capture, saving background resources.
*   **Action**: None. `mss` is already removed from `requirements.txt` and `record.py`.

### 3. Remove YouTube Functionality [ALREADY DONE]
This tool is strictly for live, in-person classroom recording, so the YouTube feature was removed to reduce unnecessary bloat.
*   **Action**: None. `youtube-transcript-api` is removed from `requirements.txt` and the frontend tab has been converted to a dedicated Capture tab.

### 4. Remove Tauri (Frontend)
Your `package.json` in the frontend contains dependencies for Tauri (`@tauri-apps/api`, `@tauri-apps/cli`) and there are `src-tauri` folders. Tauri is used to package web apps into native desktop `.exe` files. 
*   **Action**: If you are happy just running this in your Chrome/Edge browser, you can uninstall the Tauri packages and delete the `src-tauri` folders.

### 5. Remove Redundant OCR Pre-processing
Currently, `opencv` runs a complex "board corner detection and perspective warp" algorithm. If your ESP32-CAM is mounted on a tripod facing the board directly, this perspective correction is a waste of CPU cycles.
*   **Action**: You can bypass the `correct_perspective()` function in `ocr.py` to speed up processing.
