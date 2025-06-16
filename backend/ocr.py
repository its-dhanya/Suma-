import os
import logging
from PIL import Image
from pytesseract import image_to_string

# Logging
LOG_DIR = os.path.join(os.getcwd(), "logs")
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "ocr.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def ocr_image(image_path: str) -> str:
    """Returns extracted text from an image."""
    try:
        logging.info(f"Running OCR on {image_path}")
        img = Image.open(image_path)
        text = image_to_string(img)
        logging.debug(f"OCR text: {text[:50]}...")
        return text
    except Exception as e:
        logging.exception(f"OCR error: {e}")
        return ""
