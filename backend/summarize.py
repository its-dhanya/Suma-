"""
summarize.py — Enhanced structured summarisation (better output)
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

# ── Improved Prompt ───────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert educational assistant.

Convert the lecture into a WELL-STRUCTURED JSON.

STRICT RULES:
- ONLY valid JSON
- No markdown or extra text
- Keep explanations simple and student-friendly

JSON FORMAT:
{
  "title": "topic name",
  "overview": "2-3 line summary",
  "core_concepts": [
    {
      "name": "concept",
      "explanation": "simple explanation"
    }
  ],
  "examples": ["example"],
  "key_points": ["important point"],
  "applications": ["real-world usage"],
  "questions": ["possible exam question"],
  "summary": "final recap"
}
"""

# ── Ollama Call ───────────────────────────────────────────────────────

def _call_ollama(prompt: str) -> str:
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": 1024,
                    "num_thread": 2
                }
            },
            timeout=120
        )

        response.raise_for_status()
        return response.json().get("response", "").strip()

    except Exception as e:
        logging.error(f"Ollama error: {e}")
        return ""

# ── JSON Extraction ───────────────────────────────────────────────────

def _extract_json(text: str):
    try:
        start = text.find("{")
        end = text.rfind("}") + 1

        if start == -1 or end == -1:
            raise ValueError("No JSON found")

        return json.loads(text[start:end])

    except Exception as e:
        logging.error(f"JSON parsing failed: {e}")
        return {"raw": text}

# ── Public Function ───────────────────────────────────────────────────

def summarize(text: str):
    if not text.strip():
        return {"error": "Empty input"}

    text = text[:800]

    prompt = f"{SYSTEM_PROMPT}\n\nLecture:\n{text}"

    raw = _call_ollama(prompt)

    if not raw:
        return {"error": "No response"}

    return _extract_json(raw)

# ── Test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample = """
    Transfer learning allows a model trained on one task
    to be reused for another related task. Feature extraction
    and fine-tuning are two main approaches.
    """

    result = summarize(sample)
    print(json.dumps(result, indent=2))