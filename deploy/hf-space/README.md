---
title: Layout Preserving OCR API
emoji: 📄
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Layout-Preserving OCR — API

Django REST backend for the layout-preserving OCR editor.

- Upload a PDF or image, extract layout + text, edit it, export to
  PDF/DOCX/HTML/TXT/JSON.
- Digital PDFs are parsed with PyMuPDF; scanned pages run through PaddleOCR.

Source and documentation live in the main project repository.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` / `POST` | `/api/documents/` | List / upload |
| `GET` / `DELETE` | `/api/documents/<id>/` | Detail / delete |
| `GET` | `/api/documents/<id>/status/` | Extraction progress |
| `GET` / `PATCH` | `/api/documents/<id>/layout/` | Layout cache / save edits |
| `GET` | `/api/documents/<id>/pages/<n>/` | Rendered page |
| `GET` | `/api/documents/<id>/export/?export_format=pdf` | Export |

Storage is ephemeral on the free tier: uploaded files and the database are lost
when the Space restarts.
