"""
summarize.py — Context-aware structured summarisation.

Builds a timeline prompt that labels:
  - AUDIO TRANSCRIPT: what was spoken (with timestamps)
  - BOARD CONTENT: what was on the whiteboard at that moment (OCR text)

This gives the LLM the actual relationship between speech and board content
instead of treating them as one undifferentiated blob.
"""

import os
import json
import logging
import requests
from dotenv import load_dotenv

# ── Setup ─────────────────────────────────────────────────────────────

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")
OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434")

LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "summarize.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ── System Prompt ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert educational assistant helping students review a classroom lecture.

You will be given a classroom session containing:
1. AUDIO TRANSCRIPT — what the teacher/speaker said (with timestamps in seconds)
2. BOARD CONTENT — text extracted via OCR from whiteboard/presentation images captured during the session

Your job is to combine BOTH sources into a single, coherent, student-friendly summary.

STRICT RULES:
- Output ONLY valid JSON, no markdown, no extra text
- Relate the spoken audio to the board content where possible
- If OCR text appears on the board at the same time certain words were spoken, link them
- Keep explanations clear and student-friendly

JSON FORMAT:
{
  "title": "topic name inferred from content",
  "overview": "2-3 sentence summary combining what was spoken and what was written on the board",
  "core_concepts": [
    {
      "name": "concept name",
      "explanation": "simple explanation",
      "source": "audio | board | both"
    }
  ],
  "board_content_summary": "summary of what was written/shown on the board",
  "audio_content_summary": "summary of what was spoken",
  "key_points": ["important point from either source"],
  "examples": ["example mentioned in lecture or shown on board"],
  "questions": ["possible exam question based on this session"],
  "summary": "final 2-3 sentence recap integrating both audio and visual content"
}
"""

# ── Prompt Builder ─────────────────────────────────────────────────────

def build_prompt(transcript_text: str, timed_segments: list, ocr_texts: list, alignment: list) -> str:
    """
    Build a context-aware prompt that shows the relationship between
    spoken audio and board content with timestamps.
    """
    lines = [SYSTEM_PROMPT, "\n\n===== CLASSROOM SESSION DATA =====\n"]

    # Section 1: full audio transcript
    if transcript_text.strip():
        lines.append("--- AUDIO TRANSCRIPT (full) ---")
        lines.append(transcript_text.strip())
        lines.append("")

    # Section 2: timeline — what was spoken alongside what was on the board
    if alignment:
        lines.append("--- TIMELINE (audio + board content at each moment) ---")
        for entry in alignment:
            fname    = entry.get("screenshot", "")
            cap_time = entry.get("capture_time_s", 0)
            segs     = entry.get("transcript_segments", [])
            ocr_key  = f"ocr_{fname}.txt"

            # Find OCR text for this image
            board_text = entry.get("ocr_text", "").strip()

            spoken = " ".join(s.get("text", "").strip() for s in segs).strip()

            if spoken or board_text:
                lines.append(f"\n[At ~{int(cap_time)}s into session]")
                if spoken:
                    lines.append(f"  SPOKEN : {spoken}")
                if board_text:
                    lines.append(f"  BOARD  : {board_text}")
    elif ocr_texts:
        # Fallback: no alignment data, just list OCR texts labeled
        lines.append("--- BOARD CONTENT (OCR from captured images) ---")
        for i, txt in enumerate(ocr_texts, 1):
            if txt.strip():
                lines.append(f"Image {i}: {txt.strip()}")
        lines.append("")

    lines.append("\n===== END OF SESSION DATA =====")
    lines.append("\nNow generate the JSON summary:")

    return "\n".join(lines)


# ── Ollama Call ───────────────────────────────────────────────────────

def _call_ollama(prompt: str) -> str:
    try:
        logging.info("Calling Ollama model=%s url=%s prompt_len=%d", OLLAMA_MODEL, OLLAMA_URL, len(prompt))
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model":  OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx":    4096,   # increased from 1024
                    "num_thread": 4,
                    "temperature": 0.3,
                }
            },
            timeout=180
        )
        response.raise_for_status()
        raw = response.json().get("response", "").strip()
        logging.info("Ollama responded with %d chars", len(raw))
        return raw

    except Exception as e:
        logging.error("Ollama error: %s", e)
        return ""


# ── JSON Extraction ───────────────────────────────────────────────────

def _extract_json(text: str):
    try:
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found in response")
        return json.loads(text[start:end])
    except Exception as e:
        logging.error("JSON parsing failed: %s | raw=%s", e, text[:200])
        return {"raw_response": text, "error": f"JSON parse failed: {e}"}


# ── Public API ────────────────────────────────────────────────────────

def summarize(
    transcript_text: str,
    timed_segments:  list = None,
    ocr_texts:       list = None,
    alignment:       list = None,
) -> dict:
    """
    Generate a structured summary that combines audio transcript
    and board OCR content with their temporal relationship.

    Args:
        transcript_text: Full plain-text audio transcript.
        timed_segments:  List of {start, end, text} dicts from Whisper.
        ocr_texts:       List of OCR strings from each captured image.
        alignment:       List of alignment dicts from /av-alignment (includes
                         screenshot filename, capture_time_s, transcript_segments).
    """
    timed_segments = timed_segments or []
    ocr_texts      = ocr_texts or []
    alignment      = alignment or []

    if not transcript_text.strip() and not any(t.strip() for t in ocr_texts):
        return {"error": "No content — both transcript and OCR are empty"}

    prompt = build_prompt(transcript_text, timed_segments, ocr_texts, alignment)
    logging.info("Built prompt (%d chars)", len(prompt))

    raw = _call_ollama(prompt)
    if not raw:
        return {"error": "Ollama returned no response. Is the service running?"}

    return _extract_json(raw)


# ── Standalone test ───────────────────────────────────────────────────

if __name__ == "__main__":
    result = summarize(
        transcript_text="Transfer learning allows a model trained on one task to be reused for another.",
        ocr_texts=["Fine-tuning vs Feature Extraction\n- Fine-tuning: update all weights\n- Feature extraction: freeze base layers"],
        alignment=[{
            "screenshot":          "image_001.jpg",
            "capture_time_s":      10,
            "transcript_segments": [{"start": 8, "end": 15, "text": "Transfer learning allows a model trained on one task to be reused."}],
            "ocr_text":            "Fine-tuning vs Feature Extraction",
        }]
    )
    print(json.dumps(result, indent=2))