"""
ocr.py — Final Improved OCR pipeline (EasyOCR + Tesseract fallback)
"""

import os
import logging
import numpy as np
import cv2
from PIL import Image
import pytesseract
import easyocr

# ── Setup ─────────────────────────────────────────────────────────────

LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "ocr.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Initialize EasyOCR once
reader = easyocr.Reader(['en'], gpu=False)


# ── Geometry ──────────────────────────────────────────────────────────

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def four_point_transform(image, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = max(int(heightA), int(heightB))

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, M, (maxWidth, maxHeight))


def detect_board_corners(image_bgr):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    img_area = image_bgr.shape[0] * image_bgr.shape[1]

    for c in contours[:5]:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area > 0.20 * img_area:
                return approx.reshape(4, 2).astype("float32")

    return None


def correct_perspective(image_bgr):
    corners = detect_board_corners(image_bgr)
    if corners is not None:
        logging.info("Perspective correction applied")
        return four_point_transform(image_bgr, corners)

    logging.info("No board detected — skipping perspective correction")
    return image_bgr


# ── Preprocessing ─────────────────────────────────────────────────────

def enhance_for_ocr(image_bgr):
    image_bgr = cv2.resize(image_bgr, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    thresh = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        15,
        3
    )

    return thresh


# ── Cleaning ──────────────────────────────────────────────────────────

def clean_text(text):
    lines = text.split("\n")
    cleaned = []

    for line in lines:
        line = line.strip()

        if len(line) < 3:
            continue

        if not any(c.isalnum() for c in line):
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


# ── OCR Engines ───────────────────────────────────────────────────────

def easyocr_extract(image):
    results = reader.readtext(image)
    return " ".join([res[1] for res in results])


def tesseract_extract(image):
    pil_img = Image.fromarray(image)
    return pytesseract.image_to_string(pil_img, config="--oem 3 --psm 6")


# ── Main OCR ──────────────────────────────────────────────────────────

def ocr_image(image_path: str, apply_perspective_correction: bool = True) -> str:
    try:
        logging.info(f"Processing {image_path}")

        image_bgr = cv2.imread(image_path)
        if image_bgr is None:
            raise FileNotFoundError(f"Cannot load image: {image_path}")

        # Step 1: Perspective correction
        if apply_perspective_correction:
            image_bgr = correct_perspective(image_bgr)

        # Step 2: Crop borders slightly
        h, w = image_bgr.shape[:2]
        image_bgr = image_bgr[
            int(0.05*h):int(0.95*h),
            int(0.05*w):int(0.95*w)
        ]

        # Step 3: Preprocess for Tesseract
        processed = enhance_for_ocr(image_bgr)

        # Step 4: Run both OCRs
        text_easy = easyocr_extract(image_bgr)     # RAW image
        text_tess = tesseract_extract(processed)  # PROCESSED image

        # Step 5: Choose better result
        if len(text_easy.strip()) > len(text_tess.strip()):
            text = text_easy
        else:
            text = text_tess

        # Step 6: Clean
        final_text = clean_text(text)

        logging.info(f"Extracted {len(final_text)} chars")

        return final_text

    except Exception as e:
        logging.exception(f"OCR error: {e}")
        return ""


# ── TEST ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_image = "test.jpg"  # 🔥 PUT YOUR IMAGE HERE
    result = ocr_image(test_image)

    print("\n===== OCR OUTPUT =====\n")
    print(result)