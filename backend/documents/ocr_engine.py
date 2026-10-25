"""Provider-agnostic OCR for the layout pipeline.

PaddleOCR gives the best accuracy and is the default for local work, but it
needs roughly 2 GB of RAM. Hosts with a 512 MB free tier (Render's `free` plan,
for example) must offload recognition to a hosted API instead. The provider is
selected with `OCR_BACKEND`:

    paddle    local PaddleOCR (needs requirements-ocr-local.txt)
    ocrspace  OCR.space free API (OCRSPACE_API_KEY, ~25k pages/month, 1 MB/page)
    gemini    Google Gemini       (GEMINI_API_KEY)
    none      OCR disabled; scanned pages keep their embedded image only

When `OCR_BACKEND` is unset, PaddleOCR is used if it is importable and OCR is
disabled otherwise, so a slim deployment still serves digital PDFs and only
fails on pages that really need recognition.
"""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

OCR_DPI = 150
MIN_NATIVE_TEXT_CHARS = 20

# OCR.space free tier rejects anything above 1 MB, so stay just under it.
OCR_SPACE_MAX_BYTES = 950_000
OCR_UPLOAD_MAX_BYTES = int(os.environ.get("OCR_UPLOAD_MAX_BYTES", OCR_SPACE_MAX_BYTES))
OCR_TIMEOUT = int(os.environ.get("OCR_TIMEOUT", "60"))

VALID_BACKENDS = {"paddle", "ocrspace", "gemini", "none"}


def _paddle_installed():
    try:
        import paddleocr  # noqa: F401

        return True
    except Exception:
        return False


def ocr_backend():
    """Return the active OCR provider name."""
    name = (os.environ.get("OCR_BACKEND") or "").strip().lower()
    if name in VALID_BACKENDS:
        return name
    if name:
        print(f"Unknown OCR_BACKEND '{name}', ignoring it.")
    return "paddle" if _paddle_installed() else "none"


def uses_local_paddle():
    return ocr_backend() == "paddle"


def ocr_ready():
    """True when the selected provider has everything it needs to run."""
    backend = ocr_backend()
    if backend == "paddle":
        return _paddle_installed()
    if backend == "ocrspace":
        return bool((os.environ.get("OCRSPACE_API_KEY") or "").strip())
    if backend == "gemini":
        return bool((os.environ.get("GEMINI_API_KEY") or "").strip())
    return False


def page_text_char_count(elements):
    return sum(
        len((el.get("text") or "").strip())
        for el in elements
        if el.get("type") != "image"
    )


def _text_line(
    page_number, index, text, x0, y0, x1, y1, confidence=None, source="ocr"
):
    """Build one layout element; shape matches the PyMuPDF/Paddle elements."""
    height = max(1.0, y1 - y0)
    element = {
        "id": f"page-{page_number}-ocr-{index}",
        "type": "text-line",
        "text": text,
        "source": source,
        "bbox": {
            "x": round(x0, 2),
            "y": round(y0, 2),
            "width": round(max(1.0, x1 - x0), 2),
            "height": round(height, 2),
        },
        "style": {
            "fontFamily": "Times New Roman, Times, serif",
            "fontSize": round(max(8.0, min(28.0, height * 0.5)), 2),
            "color": "#000000",
            "bold": False,
            "italic": False,
        },
    }
    # Hosted engines do not report a per-line score; omit the key so the UI
    # does not claim a confidence it never measured.
    if confidence is not None:
        element["confidence"] = round(float(confidence), 4)
    return element


def render_upload_image(page, dpi_steps=(150, 120, 96, 72)):
    """Render a PyMuPDF page to JPEG bytes that fit the provider's upload cap.

    Returns (jpeg_bytes, width_px, height_px). The caller derives the point
    scale as page_width / width_px, so a downscaled image still lines up with
    the original layout.
    """
    data = b""
    pix = None
    for dpi in dpi_steps:
        pix = page.get_pixmap(dpi=dpi)
        data = pix.tobytes("jpg", jpg_quality=82)
        if len(data) <= OCR_UPLOAD_MAX_BYTES:
            break
    return data, pix.width, pix.height


def _http_json(url, payload, headers, timeout=OCR_TIMEOUT):
    request = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"OCR request failed ({err.code}): {body}") from err
    except urllib.error.URLError as err:
        raise RuntimeError(f"OCR request failed: {err.reason}") from err


# --- OCR.space ---------------------------------------------------------------


def _ocrspace_lines(document):
    results = document.get("ParsedResults") or []
    if document.get("IsErroredOnProcessing") and not results:
        detail = document.get("ErrorMessage") or document.get("ErrorDetails")
        raise RuntimeError(f"OCR.space error: {detail}")
    if not results:
        raise RuntimeError("OCR.space returned no results")

    result = results[0]
    code = result.get("FileParseExitCode")
    if code != 1 and code != "1":
        raise RuntimeError(
            f"OCR.space page error: {result.get('ErrorMessage') or result.get('ErrorDetails')}"
        )

    overlay = result.get("TextOverlay") or {}
    lines = []
    for line in overlay.get("Lines") or []:
        words = [w for w in (line.get("Words") or []) if (w.get("WordText") or "").strip()]
        if not words:
            continue
        # CJK engines emit one word per character; joining those with spaces
        # would insert gaps that are not in the document.
        joiner = "" if all(len(w["WordText"].strip()) == 1 for w in words) else " "
        text = joiner.join(w["WordText"].strip() for w in words)
        lefts = [float(w.get("Left", 0)) for w in words]
        tops = [float(w.get("Top", 0)) for w in words]
        rights = [float(w.get("Left", 0)) + float(w.get("Width", 0)) for w in words]
        bottoms = [float(w.get("Top", 0)) + float(w.get("Height", 0)) for w in words]
        lines.append((text, min(lefts), min(tops), max(rights), max(bottoms), None))

    if not lines and result.get("ParsedText"):
        # Overlay was not honoured (some engines omit it); fall back to plain
        # text stacked from the top so the page is still editable.
        for index, raw in enumerate(result["ParsedText"].splitlines()):
            text = raw.strip()
            if text:
                top = 24.0 * index
                lines.append((text, 0.0, top, 400.0, top + 16.0, None))

    return lines


def _ocrspace_elements(image_bytes, page_number, scale_x, scale_y):
    api_key = (os.environ.get("OCRSPACE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "OCRSPACE_API_KEY is not set but OCR_BACKEND=ocrspace. "
            "Create a free key at https://ocr.space/ocrapi/freekey"
        )

    payload = urllib.parse.urlencode(
        {
            "base64Image": "data:image/jpeg;base64,"
            + base64.b64encode(image_bytes).decode("ascii"),
            "language": os.environ.get("OCRSPACE_LANGUAGE", "eng"),
            "isOverlayRequired": "true",
            "isTable": "true",
            "scale": "true",
            "OCREngine": os.environ.get("OCRSPACE_ENGINE", "2"),
        }
    ).encode("utf-8")

    document = _http_json(
        os.environ.get("OCRSPACE_ENDPOINT", "https://api.ocr.space/parse/image"),
        payload,
        {
            "apikey": api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    elements = []
    for text, x0, y0, x1, y1, confidence in _ocrspace_lines(document):
        elements.append(
            _text_line(
                page_number,
                len(elements),
                text,
                x0 * scale_x,
                y0 * scale_y,
                x1 * scale_x,
                y1 * scale_y,
                confidence,
                source="ocrspace",
            )
        )
    return elements


# --- Google Gemini -----------------------------------------------------------

GEMINI_PROMPT = (
    "Extract every text line from this document page, in reading order. "
    "Return JSON only, shaped as {\"lines\": [{\"text\": \"...\", "
    "\"box\": [ymin, xmin, ymax, xmax]}]} where each box value is an integer "
    "normalised to 0-1000 relative to the image. Keep line breaks and "
    "punctuation. Do not translate or summarise."
)


def _gemini_lines(image_bytes):
    api_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set but OCR_BACKEND=gemini. "
            "Get a free key at https://aistudio.google.com/apikey"
        )

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={urllib.parse.quote(api_key)}"
    )
    payload = json.dumps(
        {
            "contents": [
                {
                    "parts": [
                        {"text": GEMINI_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": base64.b64encode(image_bytes).decode("ascii"),
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {"temperature": 0, "response_mime_type": "application/json"},
        }
    ).encode("utf-8")

    document = _http_json(
        url, payload, {"Content-Type": "application/json"}
    )

    candidates = document.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates: {document.get('promptFeedback')}")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    raw = "".join(part.get("text", "") for part in parts).strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw

    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError as err:
        raise RuntimeError(f"Gemini returned invalid JSON: {err}") from err

    lines = []
    for item in parsed.get("lines") or []:
        text = (item.get("text") or "").strip()
        box = item.get("box") or []
        if not text or len(box) != 4:
            continue
        ymin, xmin, ymax, xmax = (float(value) for value in box)
        lines.append((text, xmin, ymin, xmax, ymax, None))
    return lines


def _gemini_elements(image_bytes, page_number, scale_x, scale_y):
    width_units = 1000.0
    height_units = 1000.0
    elements = []
    for text, x0, y0, x1, y1, confidence in _gemini_lines(image_bytes):
        # Gemini boxes are normalised 0-1000 in both axes.
        elements.append(
            _text_line(
                page_number,
                len(elements),
                text,
                x0 / width_units * scale_x,
                y0 / height_units * scale_y,
                x1 / width_units * scale_x,
                y1 / height_units * scale_y,
                confidence,
                source="gemini",
            )
        )
    return elements


# --- dispatch ----------------------------------------------------------------


def ocr_upload_to_elements(image_bytes, page_number=1, scale_x=1.0, scale_y=1.0,
                           width_px=1000, height_px=1000):
    """Recognise an already-rendered page image with the configured provider."""
    backend = ocr_backend()
    if backend == "ocrspace":
        return _ocrspace_elements(image_bytes, page_number, scale_x, scale_y)
    if backend == "gemini":
        # scale_x/scale_y already carry the pixel -> point conversion; Gemini's
        # 0-1000 boxes are multiplied by the pixel size first.
        return _gemini_elements(image_bytes, page_number, width_px * scale_x,
                                height_px * scale_y)
    if backend == "none":
        raise RuntimeError(
            "OCR is disabled on this deployment (OCR_BACKEND=none); "
            "scanned pages cannot be recognised."
        )
    raise RuntimeError(f"OCR_BACKEND={backend} cannot accept rendered images")


def ocr_image_file_to_elements(file_path, page_number=1):
    """OCR a standalone image file through PyMuPDF so every provider is uniform.

    Returns (elements, width, height) in the image's own pixel coordinates,
    matching what the PaddleOCR code path returns.
    """
    import pymupdf

    with pymupdf.open(file_path) as doc:
        page = doc[0]
        image_bytes, width_px, height_px = render_upload_image(
            page, dpi_steps=(72, 60, 48, 36)
        )
        elements = ocr_upload_to_elements(
            image_bytes,
            page_number=page_number,
            scale_x=page.rect.width / width_px,
            scale_y=page.rect.height / height_px,
            width_px=width_px,
            height_px=height_px,
        )
        return elements, int(round(page.rect.width)), int(round(page.rect.height))
