# Benchmark and evaluation protocol

The project is judged on layout reconstruction as much as raw OCR, so the
benchmark records both text accuracy and throughput, and the layout/visual
checks below are done by inspection.

## 1. Test set

Aim for 12–18 pages covering the categories below. Keep the source documents and
their ground-truth text under `samples/` (not committed if the source is
copyrighted — describe them instead).

| Category | Pages | Why it is included |
|---|---|---|
| Clean printed, single column | 3 | Baseline: pipeline should be near-perfect. |
| Old / scanned / low contrast | 3 | Tests OCR robustness, skewed or faded scans. |
| Two-column article | 2 | Tests reading-order heuristic and column preservation. |
| Page with figures or photos | 2 | Tests image placement and background-scan detection. |
| Table-heavy page | 2 | Tests vector-fill extraction and cell alignment (known weak spot). |
| Mixed headings + lists + captions | 2 | Tests style preservation and reading order around headings. |
| Handwriting or noisy photo | 1–2 | Documents an honest failure mode. |

Selection rule: at least one page per category must come from a real document
(not generated), so the result is not flattered by synthetic PDFs.

## 2. Metrics

| Metric | How it is measured |
|---|---|
| OCR quality | Character Error Rate (CER) and Word Error Rate (WER) against ground truth, after whitespace normalisation. |
| Reading order | Manual check: does the exported TXT read top-to-bottom per column? Record `pass` / `fail` per multi-column page. |
| Layout fidelity | Manual side-by-side: count text blocks with visible misplacement (> 10 pt shift) per page; record block shift ratio. |
| Visual similarity | Optional SSIM between the rendered original and a screenshot of the reconstruction; report only if reproducible. |
| Editability | Does editing a block leave neighbours in place? Check 5 random blocks per page. |
| Processing time | Wall-clock seconds per page from `scripts/evaluate.py` (PaddleOCR on CPU dominates). |

## 3. Running the evaluation

```powershell
# single document
env\Scripts\python.exe scripts\evaluate.py ^
  --document samples\clean\page-01.pdf ^
  --truth samples\clean\page-01.txt ^
  --kind normal

# whole manifest
env\Scripts\python.exe scripts\evaluate.py --manifest samples\manifest.json --out results.json
```

`CER`/`WER` are computed on the concatenation of all text elements in reading
order, so a bad reading order also hurts the text score — that is intentional.

## 4. Results

Fill this after running the benchmark. Keep the raw `results.json` next to this
file when reporting.

| Document | Category | Pages | CER | WER | s/page | Reading order | Notes |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

Aggregate:

- Mean CER:
- Mean WER:
- Mean s/page (scanned):
- Mean s/page (digital):

## 5. Known failure cases to record

- Handwritten pages and photos with perspective distortion.
- Dense tables: borders are reproduced, cell semantics are not.
- Three-column layouts: the current gutter heuristic only splits two columns.
- Pages where the scan is a full-page background: the background is hidden by
  design, so the export cannot reproduce non-text marks (stamps, signatures).
- Very small fonts (< 8 pt) after OCR: font size is estimated from box height.

## 6. Reporting notes

- State the OCR model and version used (`paddleocr 3.7.0`, `PP-OCRv5_mobile`).
- Report CPU model and whether timing is CPU-only.
- Report failures honestly; the brief explicitly rewards documented limitations.
