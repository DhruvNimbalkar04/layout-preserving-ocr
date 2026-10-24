"""Measure OCR quality (CER/WER) and throughput for the layout-preserving pipeline.

Usage:
    python scripts/evaluate.py --document samples/page.pdf --truth samples/page.txt
    python scripts/evaluate.py --manifest samples/manifest.json --out results.json

A manifest is a JSON list of entries:
    [{"name": "clean-1", "document": "clean/1.pdf", "truth": "clean/1.txt",
      "kind": "normal"}]
Relative paths are resolved against the manifest file.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django

django.setup()

from documents.pymupdf_extractor import extract_document_layout  # noqa: E402


def normalize(text):
    return " ".join(text.split())


def layout_text(layout):
    parts = []
    for page in layout.get("pages", []):
        for element in page.get("elements", []):
            if element.get("type") != "image" and element.get("text"):
                parts.append(element["text"])
    return normalize(" ".join(parts))


def edit_distance(source, target):
    if len(source) < len(target):
        source, target = target, source

    previous = list(range(len(target) + 1))
    for i, source_char in enumerate(source, start=1):
        current = [i]
        for j, target_char in enumerate(target, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (source_char != target_char),
                )
            )
        previous = current
    return previous[-1]


def character_error_rate(truth, hypothesis):
    if not truth:
        return None
    return edit_distance(truth, hypothesis) / len(truth)


def word_error_rate(truth, hypothesis):
    truth_words = truth.split()
    hypothesis_words = hypothesis.split()
    if not truth_words:
        return None
    return edit_distance(truth_words, hypothesis_words) / len(truth_words)


def evaluate_entry(entry, base_dir):
    document = (base_dir / entry["document"]).resolve()
    truth_path = (base_dir / entry["truth"]).resolve()

    if not document.exists():
        raise FileNotFoundError(f"document not found: {document}")
    if not truth_path.exists():
        raise FileNotFoundError(f"ground truth not found: {truth_path}")

    truth = normalize(truth_path.read_text(encoding="utf-8"))
    kind = entry.get("kind", "normal")

    started = time.perf_counter()
    layout = extract_document_layout(str(document), use_ocr=(kind == "scanned"))
    elapsed = time.perf_counter() - started

    hypothesis = layout_text(layout)
    pages = len(layout.get("pages", []))

    return {
        "name": entry.get("name", document.stem),
        "kind": kind,
        "pages": pages,
        "seconds": round(elapsed, 3),
        "seconds_per_page": round(elapsed / pages, 3) if pages else None,
        "truth_chars": len(truth),
        "hypothesis_chars": len(hypothesis),
        "cer": _round(character_error_rate(truth, hypothesis)),
        "wer": _round(word_error_rate(truth, hypothesis)),
    }


def _round(value):
    return None if value is None else round(value, 4)


def print_table(rows):
    headers = ["name", "kind", "pages", "CER", "WER", "s/page"]
    print(f"{headers[0]:<28} {headers[1]:<8} {headers[2]:>5} {headers[3]:>7} {headers[4]:>7} {headers[5]:>7}")
    print("-" * 70)
    for row in rows:
        cer = "-" if row["cer"] is None else f"{row['cer']:.3f}"
        wer = "-" if row["wer"] is None else f"{row['wer']:.3f}"
        spp = "-" if row["seconds_per_page"] is None else f"{row['seconds_per_page']:.2f}"
        print(f"{row['name']:<28} {row['kind']:<8} {row['pages']:>5} {cer:>7} {wer:>7} {spp:>7}")

    scored = [row for row in rows if row["cer"] is not None]
    if scored:
        mean_cer = sum(row["cer"] for row in scored) / len(scored)
        mean_wer = sum(row["wer"] for row in scored) / len(scored)
        total_seconds = sum(row["seconds"] for row in rows)
        print("-" * 70)
        print(f"mean CER {mean_cer:.4f} | mean WER {mean_wer:.4f} | total {total_seconds:.1f}s")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document", help="Path to a PDF or image")
    parser.add_argument("--truth", help="Path to plain-text ground truth")
    parser.add_argument("--kind", default="normal", choices=["normal", "scanned"])
    parser.add_argument("--name", default=None)
    parser.add_argument("--manifest", help="JSON manifest of benchmark entries")
    parser.add_argument("--out", help="Write detailed results as JSON")
    args = parser.parse_args()

    if args.manifest:
        manifest_path = Path(args.manifest).resolve()
        base_dir = manifest_path.parent
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    elif args.document and args.truth:
        base_dir = Path.cwd()
        entries = [
            {
                "name": args.name or Path(args.document).stem,
                "document": args.document,
                "truth": args.truth,
                "kind": args.kind,
            }
        ]
    else:
        parser.error("provide --manifest or both --document and --truth")

    rows = []
    for entry in entries:
        row = evaluate_entry(entry, base_dir)
        rows.append(row)
        print(
            f"[{row['name']}] pages={row['pages']} "
            f"CER={row['cer']} WER={row['wer']} "
            f"{row['seconds']:.2f}s"
        )

    print()
    print_table(rows)

    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
