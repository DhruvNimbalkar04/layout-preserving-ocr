# Layout-Preserving OCR

A web application that turns scanned pages and PDFs into an **editable digital
document that keeps the original page layout**, not just plain extracted text.

- **Digital PDFs** — text, fonts and geometry are read with [PyMuPDF](https://pymupdf.readthedocs.io/).
- **Scanned pages / images** — rendered and recognised with [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR).
- Extraction runs in the background with page-by-page progress, because OCR is slow.
- Original and reconstruction sit side by side; text is editable in place.

## Features

- Image and PDF upload with server-side type, size and empty-file validation
- Multi-page PDFs with per-page progress and thumbnails
- Layout-preserving reconstruction (bboxes, font size, bold/italic, colour, images, table fills)
- Column-aware reading order for clear two-column pages
- Editable text blocks with a styling toolbar, saved back to the server
- Low-OCR-confidence lines highlighted with a dotted underline and tooltip
- Export to **PDF, DOCX, HTML, TXT** and raw layout **JSON**
- Environment-based configuration, no secrets in the repository

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 6.1, Django REST Framework, django-cors-headers |
| OCR / PDF | PaddleOCR 3.7 (PP-OCRv5 mobile), PyMuPDF |
| Frontend | React 19, Vite 8, Tailwind CSS 4, React Router, Axios |
| Storage | SQLite + local media (prototype) |

## Project structure

```
.
├── backend/
│   ├── backend/                  # settings, urls, wsgi/asgi
│   └── documents/                # models, views, serializers, tests
│       ├── pymupdf_extractor.py  # layout pipeline + PDF/HTML generation
│       └── paddleocr_engine.py   # thread-safe OCR wrapper
├── frontend/src/                 # React app (pages, components, API client)
├── docs/BENCHMARK.md             # evaluation protocol
├── scripts/evaluate.py           # CER/WER + timing harness
├── HLD.md                        # high-level design
├── render.yaml                   # Render blueprint (API + static site)
├── Dockerfile                    # single-image deployment
├── requirements.txt
└── start.bat                     # local: backend + frontend together
```

## Getting started

Prerequisites: Python 3.11+, Node.js 20+.

### 1. Configure

```bash
cp .env.example .env
```

Set `DJANGO_SECRET_KEY` in `.env` to a long random string, for example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 2. Backend

```bash
python -m venv env
env\Scripts\activate            # Windows
pip install -r requirements.txt
python backend/manage.py migrate
python backend/manage.py runserver
```

API: `http://127.0.0.1:8000/api/`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: `http://localhost:5173` (Vite proxies `/api` and `/media` to the backend).

### One command (Windows)

```bat
start.bat
```

## Configuration

Backend variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | **required** | Django secret; no fallback is baked in. |
| `DJANGO_DEBUG` | `False` | Enables debug pages and media serving. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hosts. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | empty | Comma-separated origins for admin/CSRF. |
| `CORS_ALLOWED_ORIGINS` | localhost:5173 | Comma-separated frontend origins. |
| `CORS_ALLOW_ALL_ORIGINS` | `False` | Escape hatch; keep off in production. |
| `DJANGO_UPLOAD_MAX_FILE_SIZE` | `20971520` (20 MB) | Maximum upload size. |
| `UPLOAD_ALLOWED_EXTENSIONS` | pdf, jpg, jpeg, png, bmp, tif, tiff, webp | Upload allowlist. |
| `DJANGO_SERVE_MEDIA` | `False` | Serve `/media/` through Django (demo hosts). |

Frontend: `VITE_API_BASE_URL` (default empty = same origin / dev proxy). Copy
`frontend/.env.example` to `frontend/.env.local` when pointing at a remote API.

## Tests

```bash
python backend/manage.py test documents -v 2
```

Covers upload validation (type, empty, oversize), listing, deletion, layout
save, status, exports and the reading-order heuristic.

## Evaluation

`docs/BENCHMARK.md` describes the test set and metrics. Run the harness with:

```bash
python scripts/evaluate.py --manifest samples/manifest.json --out results.json
```

It reports CER, WER and seconds per page per document.

## Deployment

### Render blueprint

`render.yaml` defines two services:

1. **API** — gunicorn + whitenoise, runs migrations at build time.
2. **Static site** — `npm ci && npm run build`, SPA rewrite to `index.html`.

Steps: push the repo, choose **New → Blueprint**, select the repository, then
set `CORS_ALLOWED_ORIGINS` to the static site URL and `VITE_API_BASE_URL` to the
API URL. Redeploy the static site after changing the frontend variable.

> PaddleOCR needs roughly **2 GB of RAM**. Free 512 MB instances will fail on
> scanned documents; use at least the Starter plan or a container host.

> Render's filesystem is **ephemeral**: uploaded files and the SQLite database do
> not survive a redeploy. Use a persistent disk or Postgres + object storage for
> anything beyond a demo.

### Docker

```bash
docker build -t layout-ocr .
docker run -p 8000:8000 \
  -e DJANGO_SECRET_KEY=change-me \
  -e DJANGO_ALLOWED_HOSTS=localhost \
  -e DJANGO_DEBUG=True \
  layout-ocr
```

## API overview

| Method | Endpoint | Description |
|---|---|---|
| GET/POST | `/api/documents/` | List documents / upload a new one |
| GET/DELETE | `/api/documents/<id>/` | Retrieve or delete a document |
| GET | `/api/documents/<id>/status/` | Extraction progress |
| GET/PATCH | `/api/documents/<id>/layout/` | Cached layout / save edits |
| GET | `/api/documents/<id>/pages/<n>/` | Rendered page image |
| GET | `/api/documents/<id>/export/?export_format=pdf` | Export (`pdf`, `docx`, `html`, `txt`, `json`) |

## Known limitations

- Text is line-based; headings, captions and lists are not classified.
- Tables are approximated from vector fills and borders, not modelled as tables.
- Reading order handles a single clear gutter only (two columns, not three).
- Handwriting and low-quality photos degrade OCR.
- No authentication; the demo is single-tenant.
- DOCX export preserves positions approximately, not exactly.

See `HLD.md` for the architecture and `docs/BENCHMARK.md` for the evaluation plan.
