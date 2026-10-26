import os

OCR_DPI = 150
MIN_NATIVE_TEXT_CHARS = 20

NO_OCR = (
    "OCR is disabled: PaddleOCR is not installed, so scanned pages cannot be "
    "recognised. Install requirements-ocr-local.txt or use a host with ~2 GB."
)


def paddle_installed():
    try:
        import paddleocr  # noqa: F401

        return True
    except Exception:
        return False


def ocr_backend():
    if (os.environ.get("OCR_BACKEND") or "").strip().lower() == "none":
        return "none"
    return "paddle" if paddle_installed() else "none"


def ocr_ready():
    return ocr_backend() == "paddle"


def page_text_char_count(elements):
    return sum(
        len((el.get("text") or "").strip())
        for el in elements
        if el.get("type") != "image"
    )
