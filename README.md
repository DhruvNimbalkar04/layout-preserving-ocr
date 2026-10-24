# Layout-Preserving OCR

A web application that extracts text from PDFs while keeping the original page
layout, lets you edit the extracted content in a page viewer, and exports the
result back out.

- **Normal PDFs** — text and layout are extracted with [PyMuPDF](https://pymupdf.readthedocs.io/).
- **Scanned PDFs** — pages are rendered to images and passed through [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR).
- Extraction runs in a background thread with progress polling, since OCR can take minutes.

## Features

- Upload a PDF and mark it as *normal* or *scanned*
- Asynchronous extraction with live page-by-page progress
- Layout-aware page viewer with editable text blocks
- Rich-text styling preserved (font size, bold, italic, alignment)
- Export to **PDF**, **DOCX**, **HTML**, **TXT**, or raw layout **JSON**
- Recent documents list and document deletion

## Tech stack

| Layer    | Technology |
| -------- | ---------- |
| Backend  | Django 6.1, Django REST Framework, django-cors-headers |
| OCR      | PaddleOCR + PaddlePaddle, PyMuPDF |
| Frontend | React 19, Vite 8, Tailwind CSS 4, React Router, Axios |
| Database | SQLite |

## Project structure

```
OCR-project/
├── backend/
│   ├── manage.py
│   ├── backend/            # Django project (settings, urls, wsgi/asgi)
│   └── documents/          # App: models, views, serializers
│       ├── pymupdf_extractor.py   # layout extraction + PDF/HTML generation
│       └── paddleocr_engine.py    # OCR engine wrapper
├── frontend/
│   └── src/
│       ├── components/     # Navbar, upload, preview, recent documents
│       ├── pages/          # Home, DocumentViewer
│       └── services/api.js # Axios API client
├── requirements.txt
└── start.bat               # Starts backend + frontend together
```

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 20+

### Backend

```bash
python -m venv env
env\Scripts\activate          # Windows
pip install -r requirements.txt
cd backend
python manage.py migrate
python manage.py runserver
```

The API is served at `http://127.0.0.1:8000/api/`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app opens at `http://localhost:5173`.

### One command (Windows)

```bat
start.bat
```

## API overview

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET/POST | `/api/documents/` | List documents / upload a new one |
| GET/DELETE | `/api/documents/<id>/` | Retrieve or delete a document |
| GET | `/api/documents/<id>/status/` | Extraction progress |
| GET/PATCH | `/api/documents/<id>/layout/` | Cached layout / save edits |
| GET | `/api/documents/<id>/pages/<n>/` | Rendered page image |
| GET | `/api/documents/<id>/export/?export_format=pdf` | Export (pdf, docx, html, txt, json) |

## Notes

- Uploaded files and the SQLite database are excluded from version control;
  run `migrate` after cloning.
- PaddleOCR downloads its models on first run, so the first scanned-PDF
  extraction is noticeably slower.
