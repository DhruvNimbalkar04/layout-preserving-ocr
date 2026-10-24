import os
import threading

import numpy as np

_engine = None
_engine_lock = threading.Lock()
# PaddleOCR predictors are not thread-safe: two concurrent predict() calls on the
# same instance can corrupt state or crash the process. Serialize inference.
_predict_lock = threading.Lock()

OCR_DPI = 150
MIN_NATIVE_TEXT_CHARS = 20

# Model presets. "mobile" is ~10x faster than the default "medium" models on CPU
# while keeping comparable layout detection quality on printed documents.
MODEL_PRESETS = {
    "mobile": ("PP-OCRv5_mobile_det", "en_PP-OCRv5_mobile_rec"),
    "small": ("PP-OCRv6_small_det", "PP-OCRv6_small_rec"),
    "medium": ("PP-OCRv6_medium_det", "PP-OCRv6_medium_rec"),
}
DEFAULT_MODEL_PRESET = "mobile"


def _selected_preset():
    name = (os.environ.get("PADDLEOCR_MODEL") or DEFAULT_MODEL_PRESET).strip().lower()
    return name if name in MODEL_PRESETS else DEFAULT_MODEL_PRESET


def get_ocr_engine():
    """Load PaddleOCR once and reuse it across requests."""
    global _engine
    if _engine is not None:
        return _engine

    with _engine_lock:
        if _engine is not None:
            return _engine

        from paddleocr import PaddleOCR

        lang = os.environ.get("PADDLEOCR_LANG", "en")
        base_kwargs = {
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
            "enable_mkldnn": True,
        }
        cpu_threads = os.environ.get("PADDLEOCR_CPU_THREADS")
        if cpu_threads:
            base_kwargs["cpu_threads"] = int(cpu_threads)

        preset = _selected_preset()
        det_name, rec_name = MODEL_PRESETS[preset]

        if lang == "en":
            try:
                _engine = PaddleOCR(
                    text_detection_model_name=det_name,
                    text_recognition_model_name=rec_name,
                    **base_kwargs,
                )
                return _engine
            except Exception as err:
                print(
                    f"PaddleOCR preset '{preset}' unavailable ({err}); "
                    "falling back to default models."
                )

        _engine = PaddleOCR(lang=lang, **base_kwargs)
        return _engine


def pixmap_to_rgb(pix):
    samples = np.frombuffer(pix.samples, dtype=np.uint8)
    img = samples.reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        return img[:, :, :3]
    if pix.n == 1:
        return np.repeat(img, 3, axis=2)
    return img


def _poly_bbox(poly):
    pts = np.array(poly, dtype=float).reshape(-1, 2)
    x0, y0 = pts.min(axis=0)
    x1, y1 = pts.max(axis=0)
    return float(x0), float(y0), float(x1), float(y1)


def _box_bbox(box):
    vals = np.array(box, dtype=float).reshape(-1)
    if vals.size >= 4:
        return float(vals[0]), float(vals[1]), float(vals[2]), float(vals[3])
    return 0.0, 0.0, 0.0, 0.0


def ocr_image_to_elements(image, page_number=1, scale_x=1.0, scale_y=1.0):
    """Run PaddleOCR on an RGB numpy image and return layout text-line elements."""
    engine = get_ocr_engine()
    with _predict_lock:
        results = engine.predict(image)
    if not results:
        return []

    result = results[0]
    texts = list(result.get("rec_texts") or [])
    scores = list(result.get("rec_scores") or [])
    boxes = result.get("rec_boxes")
    polys = result.get("rec_polys") or result.get("dt_polys")

    elements = []
    for idx, text in enumerate(texts):
        text = (text or "").strip()
        if not text:
            continue

        score = float(scores[idx]) if idx < len(scores) else 1.0
        if boxes is not None and idx < len(boxes):
            x0, y0, x1, y1 = _box_bbox(boxes[idx])
        elif polys is not None and idx < len(polys):
            x0, y0, x1, y1 = _poly_bbox(polys[idx])
        else:
            continue

        x0 *= scale_x
        x1 *= scale_x
        y0 *= scale_y
        y1 *= scale_y
        height = max(1.0, y1 - y0)

        elements.append({
            "id": f"page-{page_number}-ocr-{len(elements)}",
            "type": "text-line",
            "text": text,
            "confidence": round(score, 4),
            "source": "paddleocr",
            "bbox": {
                "x": round(x0, 2),
                "y": round(y0, 2),
                "width": round(max(1.0, x1 - x0), 2),
                "height": round(height, 2),
            },
            "style": {
                "fontFamily": "Times New Roman, Times, serif",
                # OCR boxes are inflated by the detector's unclip ratio, so the
                # box height is roughly twice the font size.
                "fontSize": round(max(8.0, min(28.0, height * 0.5)), 2),
                "color": "#000000",
                "bold": False,
                "italic": False,
            },
        })

    return elements


def ocr_file_to_elements(file_path, page_number=1):
    import cv2

    image = cv2.imread(file_path)
    if image is None:
        return [], 0, 0

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    height, width = rgb.shape[:2]
    return ocr_image_to_elements(rgb, page_number=page_number), width, height


def page_text_char_count(elements):
    return sum(len((el.get("text") or "").strip()) for el in elements if el.get("type") != "image")
