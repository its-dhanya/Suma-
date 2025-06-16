import os
import logging
from dotenv import load_dotenv

try:
    import whisper
except ImportError:
    whisper = None

load_dotenv()

OPENAI_MODEL = os.getenv("WHISPER_MODEL", "base")

LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "transcribe.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def transcribe(audio_path: str) -> str:
    """Returns and stores transcription text for the given audio file."""
    if whisper is None:
        logging.error("Whisper not installed.")
        return ""

    try:
        logging.info(f"Loading Whisper model '{OPENAI_MODEL}'")
        model = whisper.load_model(OPENAI_MODEL)

        logging.info(f"Transcribing {audio_path}")
        result = model.transcribe(audio_path)

        text = result.get('text', '')
        logging.info("Transcription complete.")

        # Save transcription to .txt file
        transcript_path = os.path.splitext(audio_path)[0] + ".txt"
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(text)
        logging.info(f"Transcript saved to {transcript_path}")

        return text

    except Exception as e:
        logging.exception(f"Transcription error: {e}")
        return ""
