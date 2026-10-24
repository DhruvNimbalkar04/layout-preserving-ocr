import os
import base64
import pymupdf

from .paddleocr_engine import (
    MIN_NATIVE_TEXT_CHARS,
    OCR_DPI,
    ocr_file_to_elements,
    ocr_image_to_elements,
    page_text_char_count,
    pixmap_to_rgb,
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

# Bump when the layout structure or element semantics change so cached layouts
# from older extractors are rebuilt on next open.
LAYOUT_VERSION = 3


def clean_font_family(font_name):
    if not font_name:
        return "Times New Roman, Times, serif"
    fn = font_name
    if "+" in fn:
        fn = fn.split("+", 1)[1]
    for sfx in [",BoldItalic", ",Bold", ",Italic", "-BoldItalic", "-Bold", "-Italic", "-Regular", "MT", "PS"]:
        fn = fn.replace(sfx, "")
    fn = fn.strip()

    fn_lower = fn.lower()
    if any(k in fn_lower for k in ["times", "roman", "cambria", "georgia", "serif"]):
        return "Times New Roman, Times, serif"
    elif any(k in fn_lower for k in ["courier", "mono", "consolas"]):
        return "Courier New, monospace"
    elif any(k in fn_lower for k in ["arial", "helv", "montserrat", "calibri", "sans"]):
        return f"{fn}, Arial, sans-serif"
    return f"{fn}, sans-serif"


def _apply_reading_order(elements, page_width):
    """Sort text lines into column-major order when a clear vertical gutter exists.

    Detectors return lines in raw detection order (usually top-to-bottom across the
    whole page), which interleaves columns. Reordering only happens when the page
    looks genuinely multi-column, so single-column pages keep their original order.
    """
    text = [el for el in elements if el.get("type") == "text-line"]
    if len(text) < 8 or page_width <= 0:
        return elements

    body = [el for el in text if el["bbox"]["width"] <= 0.55 * page_width]
    if len(body) < max(6, int(len(text) * 0.7)):
        return elements

    bins = 100
    covered = [False] * bins
    for el in body:
        start = max(0, int(el["bbox"]["x"] / page_width * bins))
        end = min(bins - 1, int((el["bbox"]["x"] + el["bbox"]["width"]) / page_width * bins))
        for index in range(start, end + 1):
            covered[index] = True

    best_start, best_len, run_start = None, 0, None
    for index, is_covered in enumerate(covered + [True]):
        if not is_covered and run_start is None:
            run_start = index
        elif is_covered and run_start is not None:
            run_len = index - run_start
            if run_len > best_len:
                best_start, best_len = run_start, run_len
            run_start = None

    if best_len < 4:
        return elements

    gap_center = (best_start + best_len / 2) / bins * page_width
    if not (0.2 * page_width <= gap_center <= 0.8 * page_width):
        return elements

    def column_of(el):
        box = el["bbox"]
        return 0 if box["x"] + box["width"] / 2 < gap_center else 1

    left = [el for el in text if column_of(el) == 0]
    right = [el for el in text if column_of(el) == 1]
    if len(left) < 3 or len(right) < 3:
        return elements

    ordered = sorted(
        text,
        key=lambda el: (
            column_of(el),
            el["bbox"]["y"] - el["bbox"]["height"] * 0.5,
            el["bbox"]["x"],
        ),
    )

    ordered_iter = iter(ordered)
    return [
        next(ordered_iter) if el.get("type") == "text-line" else el
        for el in elements
    ]


def _ocr_pdf_page(page, page_number):
    pix = page.get_pixmap(dpi=OCR_DPI)
    rgb = pixmap_to_rgb(pix)
    scale = 72.0 / OCR_DPI
    return ocr_image_to_elements(rgb, page_number=page_number, scale_x=scale, scale_y=scale)


def extract_document_layout(file_path, use_ocr=False, on_progress=None):
    ext = os.path.splitext(file_path)[1].lower()
    if ext in IMAGE_EXTS:
        elements, width, height = ocr_file_to_elements(file_path, page_number=1)
        if on_progress:
            on_progress(1, 1)
        return {
            "pages": [{
                "page_number": 1,
                "width": float(width or 595.2),
                "height": float(height or 841.92),
                "elements": _apply_reading_order(elements, width or 595.2),
            }],
            "ocr_engine": "paddleocr",
            "layout_version": LAYOUT_VERSION,
        }

    pages = []
    used_ocr = False

    with pymupdf.open(file_path) as doc:
        total_pages = len(doc)
        for page_number, page in enumerate(doc, start=1):
            elements = []
            dict_data = page.get_text("dict")

            for block in dict_data.get("blocks", []):
                block_type = block.get("type", 0)

                # Type 1: Image block
                if block_type == 1:
                    x0, y0, x1, y1 = block["bbox"]
                    img_bytes = block.get("image")
                    ext = block.get("ext", "png").lower()
                    if ext == "jpg":
                        ext = "jpeg"

                    if not img_bytes:
                        xref = block.get("xref", 0)
                        if xref and xref > 0:
                            try:
                                base_image = doc.extract_image(xref)
                                img_bytes = base_image.get("image")
                                ext = base_image.get("ext", ext).lower()
                            except Exception:
                                pass

                    if img_bytes:
                        b64_str = base64.b64encode(img_bytes).decode("ascii")
                        mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"
                        data_uri = f"data:{mime};base64,{b64_str}"

                        # A scan of a whole page is embedded as one large image.
                        # Flag it so it can be hidden behind reconstructed text
                        # instead of being drawn underneath it.
                        is_background = (
                            (x1 - x0) >= page.rect.width * 0.85
                            and (y1 - y0) >= page.rect.height * 0.85
                        )

                        elements.append({
                            "id": f"page-{page_number}-img-{len(elements)}",
                            "type": "image",
                            "src": data_uri,
                            "bbox": {
                                "x": round(x0, 2),
                                "y": round(y0, 2),
                                "width": round(x1 - x0, 2),
                                "height": round(y1 - y0, 2),
                            },
                            "isBackground": is_background,
                            "style": {
                                "opacity": 1.0,
                            },
                        })

                # Type 0: Text block
                elif block_type == 0:
                    for line in block.get("lines", []):
                        spans = line.get("spans", [])
                        text = "".join(span.get("text", "") for span in spans).strip()

                        if not text:
                            continue

                        x0, y0, x1, y1 = line["bbox"]
                        style = spans[0] if spans else {}
                        color = style.get("color", 0)
                        font_raw = style.get("font", "")

                        elements.append({
                            "id": f"page-{page_number}-el-{len(elements)}",
                            "type": "text-line",
                            "text": text,
                            "bbox": {
                                "x": round(x0, 2),
                                "y": round(y0, 2),
                                "width": round(x1 - x0, 2),
                                "height": round(y1 - y0, 2),
                            },
                            "style": {
                                "fontFamily": clean_font_family(font_raw),
                                "fontSize": round(style.get("size", 12), 2),
                                "color": f"#{color:06x}",
                                "bold": "Bold" in font_raw or style.get("flags", 0) & 2 != 0,
                                "italic": "Italic" in font_raw or style.get("flags", 0) & 1 != 0,
                            },
                        })

            # Extract vector drawings (table borders, dividers, cell fills)
            try:
                for d in page.get_drawings():
                    r = d.get("rect")
                    if not r:
                        continue
                    if r.width >= page.rect.width - 5 and r.height >= page.rect.height - 5:
                        continue

                    fill = d.get("fill")
                    color = d.get("color")

                    if fill and len(fill) >= 3 and r.width > 5 and r.height > 5 and r.width < page.rect.width - 10:
                        hex_fill = f"#{int(fill[0]*255):02x}{int(fill[1]*255):02x}{int(fill[2]*255):02x}"
                        elements.append({
                            "id": f"page-{page_number}-fill-{len(elements)}",
                            "type": "fill",
                            "bbox": {
                                "x": round(r.x0, 2),
                                "y": round(r.y0, 2),
                                "width": round(r.width, 2),
                                "height": round(r.height, 2),
                            },
                            "color": hex_fill,
                        })
            except Exception:
                pass

            native_chars = page_text_char_count(elements)
            # OCR only when the page is image-only / nearly empty. Digital PDFs
            # (including CVs uploaded as "scanned") already have selectable text.
            needs_ocr = native_chars < MIN_NATIVE_TEXT_CHARS
            if needs_ocr and (use_ocr or native_chars == 0):
                try:
                    ocr_elements = _ocr_pdf_page(page, page_number)
                    if ocr_elements:
                        used_ocr = True
                        # Drop the full-page scan: the OCR text replaces it, so
                        # keeping it would render text over the original scan.
                        non_text = [
                            el for el in elements
                            if el.get("type") == "fill"
                            or (el.get("type") == "image" and not el.get("isBackground"))
                        ]
                        elements = non_text + ocr_elements
                except Exception as err:
                    print(f"OCR failed on page {page_number}, keeping native text: {err}")

            elements = _apply_reading_order(elements, page.rect.width)

            pages.append({
                "page_number": page_number,
                "width": round(page.rect.width, 2),
                "height": round(page.rect.height, 2),
                "elements": elements,
            })

            if on_progress:
                on_progress(page_number, total_pages)

    return {
        "pages": pages,
        "ocr_engine": "paddleocr" if used_ocr else "pymupdf",
        "layout_version": LAYOUT_VERSION,
    }


def render_page_image(file_path, page_num):
    if os.path.splitext(file_path)[1].lower() != ".pdf":
        if page_num != 1:
            return None, None

        extension = os.path.splitext(file_path)[1].lower()
        content_type = "image/jpeg" if extension in (".jpg", ".jpeg") else f"image/{extension[1:]}"

        with open(file_path, "rb") as image:
            return image.read(), content_type

    with pymupdf.open(file_path) as doc:
        page_index = page_num - 1

        if not 0 <= page_index < len(doc):
            return None, None

        image = doc[page_index].get_pixmap(dpi=150, alpha=False)
        return image.tobytes("png"), "image/png"


def generate_reconstructed_pdf(document, layout):
    """Reconstructs a new PDF document from layout elements (text and images)."""
    new_doc = pymupdf.open()
    pages = layout.get("pages", [])

    for page_data in pages:
        width = page_data.get("width", 595.32)
        height = page_data.get("height", 841.92)
        pdf_page = new_doc.new_page(width=width, height=height)

        # Place images first
        for el in page_data.get("elements", []):
            if el.get("type") == "image":
                if el.get("isBackground"):
                    continue
                src = el.get("src", "")
                if src.startswith("data:"):
                    try:
                        _, b64_data = src.split(",", 1)
                        img_bytes = base64.b64decode(b64_data)
                        bbox = el.get("bbox", {})
                        rect = pymupdf.Rect(
                            bbox.get("x", 0),
                            bbox.get("y", 0),
                            bbox.get("x", 0) + bbox.get("width", 100),
                            bbox.get("y", 0) + bbox.get("height", 100),
                        )
                        pdf_page.insert_image(rect, stream=img_bytes)
                    except Exception as err:
                        print("Error inserting image in export PDF:", err)

        # Place text elements
        for el in page_data.get("elements", []):
            if el.get("type") != "image" and el.get("text"):
                bbox = el.get("bbox", {})
                style = el.get("style", {})
                fontsize = style.get("fontSize", 12)
                text = el.get("text", "")

                # Keep the line inside the page: shrink it if it would overflow.
                available = max(40.0, width - bbox.get("x", 0) - 18)
                try:
                    text_width = pymupdf.get_text_length(text, fontname="helv", fontsize=fontsize)
                    if text_width > available:
                        fontsize = max(6.0, fontsize * available / text_width)
                except Exception:
                    pass

                # Baseline offset
                pt = pymupdf.Point(bbox.get("x", 0), bbox.get("y", 0) + fontsize)
                try:
                    pdf_page.insert_text(
                        pt,
                        text,
                        fontsize=fontsize,
                        fontname="helv",
                    )
                except Exception as err:
                    print("Error inserting text in export PDF:", err)

    return new_doc.tobytes()


def generate_layout_html(layout, title="Reconstructed Document"):
    """Generates standalone responsive HTML preserving the document layout."""
    pages_html = []
    for page in layout.get("pages", []):
        width = page.get("width", 800)
        height = page.get("height", 1100)
        elements_html = []

        for el in page.get("elements", []):
            bbox = el.get("bbox", {})
            x = bbox.get("x", 0)
            y = bbox.get("y", 0)
            w = bbox.get("width", 100)
            h = bbox.get("height", 20)

            if el.get("type") == "image":
                if el.get("isBackground"):
                    continue
                src = el.get("src", "")
                z_index = 1 if el.get("isBackground") else 2
                elements_html.append(
                    f'<img src="{src}" style="position:absolute;left:{x}px;top:{y}px;'
                    f'width:{w}px;height:{h}px;object-fit:contain;z-index:{z_index};" />'
                )
            else:
                text = el.get("text", "").replace("<", "&lt;").replace(">", "&gt;")
                style = el.get("style", {})
                fs = style.get("fontSize", 12)
                ff = style.get("fontFamily", "sans-serif")
                fw = "bold" if style.get("bold") else "normal"
                fst = "italic" if style.get("italic") else "normal"
                col = style.get("color", "#000000")

                elements_html.append(
                    f'<div style="position:absolute;left:{x}px;top:{y}px;width:{w}px;min-height:{h}px;'
                    f'font-size:{fs}px;font-family:{ff};font-weight:{fw};font-style:{fst};color:{col};'
                    f'line-height:1.2;white-space:pre-wrap;overflow-wrap:anywhere;z-index:10;">{text}</div>'
                )

        pages_html.append(
            f'<div style="position:relative;width:{width}px;height:{height}px;background:#fff;'
            f'margin:20px auto;box-shadow:0 4px 6px -1px rgba(0,0,0,0.1);border:1px solid #e5e7eb;">'
            f'{"".join(elements_html)}</div>'
        )

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ background: #f3f4f6; margin: 0; padding: 20px; font-family: system-ui, sans-serif; }}
  </style>
</head>
<body>
  {"".join(pages_html)}
</body>
</html>"""