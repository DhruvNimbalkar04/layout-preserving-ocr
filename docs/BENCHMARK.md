# Benchmark and Evaluation

I evaluated the project on both text extraction and layout reconstruction. I used a mix of digital PDFs, scanned pages, and a handwritten form. I also compared the reconstructed pages with the originals.

## Test set

I evaluated 13 pages from four real documents. I did not add synthetic pages to fill gaps. The documents include clean printed pages, table-heavy pages, one scanned printed page, and one scanned form with handwriting. The source files and transcriptions are kept in `samples/` and are not committed because some contain personal information.

This is a useful first look at the system, but the test set is incomplete. I did not have samples for two-column articles or photo-heavy pages, and I tested only one older or low-contrast scan.

## How I measured the results

I compared extracted text with reference text using character error rate (CER) and word error rate (WER), after normalizing whitespace. For digital PDFs, I used the PDF’s embedded text as the reference. A zero score means the pipeline preserved that text; it does not measure OCR accuracy.

For scanned pages, I compared the output with manual transcriptions. I also checked reading order and processing time. I inspected layout side by side, but I did not calculate SSIM or layout IoU because I do not have annotated layout ground truth.

## Results

I ran the evaluation on October 24, 2026, using Python 3.12.10 on Windows 11 with a 13th Gen Intel Core i5-13450HX and 16 GB of RAM. The run used the CPU, PaddleOCR 3.7.0, the PP-OCRv5 mobile models, and a render resolution of 150 DPI.

The digital PDFs performed well. Across 11 pages, the mean CER was 0.0006 and the mean WER was 0.0035. Processing took an average of about 0.06 seconds per page. These results come from PyMuPDF’s native text extraction, not OCR.

The scanned printed page had a CER of 0.007 and a WER of 0.042. It took about 13.31 seconds to process. The page was a phone photo with a finger in the frame, a shadow, and slight skew. Most word errors came from words being joined around punctuation, such as `4.1INTRODUCTION` and `EXPENDITURE.METHOD`. The system also missed two bullet symbols.

The handwritten form was the weakest result. It had a CER of 0.435 and a WER of 0.485, and took about 10.25 seconds to process. The system misread several handwritten answers and sometimes placed an answer after the next question. The low-confidence indicators were useful here: the handwritten lines that were misread had confidence scores below 0.80.

Across all 13 pages, the mean CER was 0.034 and the mean WER was 0.041. Those averages are heavily affected by the handwritten form, so I would use the printed-page results when describing performance on printed text.

## What I have not tested

I did not have two-column samples, so I cannot say whether the reading-order heuristic works reliably on them. I also did not have photo-heavy pages, so image placement on those pages remains untested.

The test set includes two table-heavy pages and ten pages with mixed headings, lists, or callouts. This is enough for an initial check, but not enough to claim that all table or mixed-layout documents will work well.

I checked the visual output by comparing pages side by side. I did not report layout IoU or SSIM because I do not have annotated layout references to calculate those scores fairly.

## Limitations and failures I observed

Handwriting is the clearest failure case. For example, the system changed “mole on left leg toe” to “mole on lattr leg toe,” and misread “B +ve” as “13√2.” A small italic instruction line on the form was missed entirely.

On the scanned printed page, punctuation sometimes caused neighboring words to run together. Bullet symbols and a lone chapter number were also missed. On the handwritten form, questions and answers were occasionally returned in the wrong order because they appeared on the same scan line.

The layout handling also has limits. The reading-order logic is designed for a simple two-column split, and I have not validated it on two-column samples. It does not handle three-column layouts. Dense tables may retain some borders or fills, but the system does not reconstruct table cells or their meaning.

When a full-page scan is treated as a background image, the reconstructed export hides that image so OCR text can be placed on the page. This can also remove non-text details such as stamps and signatures. OCR font sizes are estimated from bounding-box height, so very small text may not be represented accurately.

## Next steps

I need to test more scanned pages, including older or low-contrast scans, two-column articles, and pages with photos. I should also expand the handwritten and table examples. For a stronger evaluation, I would record text accuracy, reading order, processing time, and memory use for each page. I would create annotated layout references before reporting layout similarity scores.