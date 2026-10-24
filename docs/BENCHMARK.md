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

**Run:** 2026-10-24 · `python scripts/evaluate.py --manifest docs/benchmark-manifest.json --out docs/results.json --warmup`
**Machine:** 13th Gen Intel Core i5-13450HX, 16 GB RAM, Windows 11, Python 3.12.10 — CPU only, no GPU.
**OCR stack:** `paddleocr 3.7.0`, `PP-OCRv5_mobile` detection + `en_PP-OCRv5_mobile` recognition, pages rendered at 150 DPI.
**Raw output:** `docs/results.json` · **Manifest:** `docs/benchmark-manifest.json`

The source PDFs and truth files live in `samples/` and are **not committed** (one
document is a personal CV, another a medical form); `samples/` is gitignored.
The manifest records the exact page range and provenance of every entry.

> **Read the digital scores carefully.** For digital PDFs the ground truth is the
> PDF's own embedded text layer, so CER = 0.000 means "the pipeline lost no
> characters and kept the source order", not "OCR is perfect". OCR accuracy is
> only measured on the scanned entries, where the truth is an independent manual
> transcription.

### 4.1 Per-document results

| Document | Category | Truth source | Pages | CER | WER | s/page | Reading order | Notes |
|---|---|---|---|---|---|---|---|---|
| `cv_p1` | Clean printed, single column | Embedded text layer | 1 | 0.000 | 0.000 | 0.07 | pass | 3,288 chars recovered exactly, no images |
| `brief_p1` | Table-heavy digital page | Embedded text layer | 1 | 0.000 | 0.000 | 0.06 | pass | Two bordered tables + logo; table rows kept in source order |
| `brief_p2` | Table-heavy digital page | Embedded text layer | 1 | 0.000 | 0.000 | 0.06 | pass | Heading levels + a two-column table |
| `brief_p3`–`p10` | Clean printed, single column | Embedded text layer | 8 | 0.000 | 0.000 | 0.05 (0.02–0.07) | pass | Mixed headings, lists, callout boxes |
| `pro_p1` | Scanned / photographed printed page | Manual transcription | 1 | 0.007 | 0.042 | 13.31 | pass | 42 lines, none below 0.80 confidence |
| `newdoc_p1` | Scanned form with handwriting | Manual transcription | 1 | **0.435** | **0.485** | 10.25 | partial | 8 of 65 lines below 0.80 confidence |

### 4.2 Aggregate

| Metric | All 13 pages | Excluding the handwriting case |
|---|---|---|
| Mean CER | 0.034 | **0.0006** |
| Mean WER | 0.041 | **0.0035** |
| Mean s/page, digital (11 pages) | 0.06 | 0.06 |
| Mean s/page, scanned (2 pages) | 11.8 | 13.3 |

The overall mean is dominated by one deliberately hard page; the per-category
split above is the number that should be quoted for printed documents.

### 4.3 Coverage against the test-set plan (§1)

| Category | Target | Covered | Verdict |
|---|---|---|---|
| Clean printed, single column | 3 | 10 | met |
| Old / scanned / low contrast | 3 | 1 | **under target** |
| Two-column article | 2 | 0 | **not covered** |
| Page with figures or photos | 2 | 0 photo pages (logo images only) | **not covered** |
| Table-heavy page | 2 | 2 | met |
| Mixed headings + lists + captions | 2 | 10 | met |
| Handwriting or noisy photo | 1–2 | 1 | met |

13 pages were measured, inside the 12–18 target, but only two of them are scans
and only four source documents exist. No synthetic pages were generated to pad
the set, so two-column reading order and photo-heavy placement remain
**unvalidated by measurement** — the code paths exist, the samples do not.

### 4.4 What the numbers show

- **Digital PDFs are effectively lossless.** 0.06 s/page, no characters lost,
  source order preserved, including both table pages. This is PyMuPDF doing the
  work, not OCR.
- **Scanned printed text is strong.** 0.7% CER on a phone photo with a finger in
  frame, a shadow and slight skew. The 4.2% WER is almost entirely token joining
  around punctuation (`4.1INTRODUCTION`, `EXPENDITURE.METHOD`, `1.Value`,
  `2Income`) plus two dropped bullet glyphs — no actual word was misrecognised.
- **Handwriting is the failure mode.** 43.5% CER. The confidence scores agree
  with the errors: the lowest lines (0.325, 0.522, 0.671, 0.741) are exactly the
  handwritten answers, which is what the dotted-underline UI is for.
- **Layout metrics were not invented.** Region IoU and SSIM need an annotated
  layout ground truth that this project does not have, so they are reported as
  not measured rather than estimated. Text metrics, reading order and timing are
  measured; visual fidelity was checked by side-by-side inspection only.

## 5. Known failure cases to record

- Handwritten pages and photos with perspective distortion.
- Dense tables: borders are reproduced, cell semantics are not.
- Three-column layouts: the current gutter heuristic only splits two columns.
- Pages where the scan is a full-page background: the background is hidden by
  design, so the export cannot reproduce non-text marks (stamps, signatures).
- Very small fonts (< 8 pt) after OCR: font size is estimated from box height.

### 5.1 Observed on the 2026-10-24 run

| Failure | Where | Evidence |
|---|---|---|
| Handwritten field misread | `newdoc_p1` | "mole on left leg toe" → "mole on lattr leg toe"; "Birth mark on left forearm" → "Birtn mork / letf forarm"; "B +ve" → "13√2" |
| Small italic instruction line dropped entirely | `newdoc_p1` | The "[To be filled in by a registered medical practitioner…]" header is absent from the reconstruction |
| Tokens glued across punctuation | `pro_p1` | `EXPENDITURE.METHOD`, `4.1INTRODUCTION`, `1.Value`, `2Income` — inflates WER while CER stays low |
| Bullet glyphs and lone page numbers dropped | `pro_p1` | Leading `•` markers and the "4" chapter number are not detected |
| Form reading order interleaved | `newdoc_p1` | Answers are sometimes emitted after the next question because they share a scan line |
| Two-column reading order untested | — | No two-column sample was available; heuristic is implemented but not validated |
| Layout IoU / SSIM not measured | all | No annotated layout ground truth; deliberately not estimated |

The low-confidence flagging behaved as designed on the failure case: every
handwritten field that was misread also scored below 0.80 and would be
highlighted in the editor.

## 6. Reporting notes

- State the OCR model and version used (`paddleocr 3.7.0`, `PP-OCRv5_mobile`).
- Report CPU model and whether timing is CPU-only.
- Report failures honestly; the brief explicitly rewards documented limitations.
