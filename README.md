# Layout-Preserving OCR

A web application that turns scanned pages and PDFs into an **editable digital
document that keeps the original page layout**, not just plain extracted text.

- **Digital PDFs** — text, fonts and geometry are read with [PyMuPDF](https://pymupdf.readthedocs.io/).
- **Scanned pages / images** — rendered and recognised with [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR),
  or a hosted OCR API when the host cannot spare the ~2 GB PaddleOCR needs.
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
| OCR / PDF | PyMuPDF for layout, PaddleOCR 3.7 (PP-OCRv5 mobile) for scans |
| Frontend | React 19, Vite 8, Tailwind CSS 4, React Router, Axios |
| Storage | SQLite + local media (prototype) |

## Project structure

```
.
├── backend/
│   ├── backend/                  # settings, urls, wsgi/asgi
│   └── documents/                # models, views, serializers, tests
│       ├── pymupdf_extractor.py  # layout pipeline + PDF/HTML generation
│       ├── ocr_engine.py         # OCR provider selection (paddle/none)
│       └── paddleocr_engine.py   # thread-safe local PaddleOCR wrapper
├── frontend/src/                 # React app (pages, components, API client)
├── docs/BENCHMARK.md             # protocol + measured results
├── scripts/evaluate.py           # CER/WER + timing harness
├── HLD.md                        # high-level design
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
pip install -r requirements-ocr-local.txt   # full local OCR (~2 GB RAM)
python backend/manage.py migrate
python backend/manage.py runserver
```

`requirements.txt` alone is the slim runtime (PyMuPDF + Django, no PaddleOCR);
use it when OCR is delegated to a hosted API. `requirements-ocr-local.txt` adds
PaddleOCR for in-process recognition.

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
| `CORS_ALLOWED_ORIGIN_REGEXES` | empty | Regex origins, e.g. preview deploys. |
| `CORS_ALLOW_ALL_ORIGINS` | `False` | Escape hatch; keep off in production. |
| `DJANGO_UPLOAD_MAX_FILE_SIZE` | `20971520` (20 MB) | Maximum upload size. |
| `UPLOAD_ALLOWED_EXTENSIONS` | pdf, jpg, jpeg, png, bmp, tif, tiff, webp | Upload allowlist. |
| `DJANGO_SERVE_MEDIA` | `False` | Serve `/media/` through Django (demo hosts). |
| `OCR_BACKEND` | auto | `paddle` or `none`. Empty = PaddleOCR if installed, else `none`. |

Frontend: `VITE_API_BASE_URL` (default empty = same origin / dev proxy). Copy
`frontend/.env.example` to `frontend/.env.local` when pointing at a remote API.

## Tests

```bash
python backend/manage.py test documents -v 2
```

Covers upload validation (type, empty, oversize), listing, deletion, layout
save, status, exports and the reading-order heuristic.

## Evaluation

`docs/BENCHMARK.md` describes the test set, the metrics and the measured
results. Latest run (2026-10-24, CPU only):

- Digital PDFs: **CER 0.000**, 0.06 s/page over 11 pages (text is lossless; this
  measures ordering/loss, not OCR accuracy).
- Photographed textbook page: **CER 0.007**, WER 0.042, 13.3 s/page.
- Handwritten form: **CER 0.435** — the documented failure mode.
- 13 pages total across four real documents; two-column and photo-heavy layouts
  are not yet covered.

Raw numbers are in `docs/results.json`; the run manifest is
`docs/benchmark-manifest.json`.

```bash
python scripts/evaluate.py --manifest docs/benchmark-manifest.json --out docs/results.json --warmup
```

`samples/` is gitignored because the source documents are personal, so point the
manifest at your own pages to reproduce. `--warmup` loads PaddleOCR before timing
so the first scanned page is not charged for model initialisation.

## Deployment

Two processes: the Django API (gunicorn + whitenoise) and a static Vite build.

**Backend**

```bash
pip install -r requirements.txt
python backend/manage.py migrate
python backend/manage.py collectstatic --noinput
gunicorn --chdir backend backend.wsgi --log-file -
```

Set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`.
Add `DJANGO_SERVE_MEDIA=True` only if the host cannot serve `/media/` itself.

**Frontend**

```bash
cd frontend && npm ci && npm run build
```

Publish `frontend/dist` as a static site with a rewrite of `/*` to
`/index.html`, and build with `VITE_API_BASE_URL` pointing at the API URL.

> PaddleOCR needs roughly **2 GB of RAM**, so it cannot run on a 512 MB tier.
> Digital PDFs keep working there because PyMuPDF parses them in-process;
> scanned pages are reported as unsupported. Recognising scans needs a backend
> plan with more memory.

> Most demo hosts use an **ephemeral filesystem**: uploaded files and the SQLite
> database do not survive a redeploy. Use a persistent disk or Postgres + object
> storage for anything beyond a demo.

### Render (free plan)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/DhruvNimbalkar04/layout-preserving-ocr)

`render.yaml` in the repo root is a ready Blueprint for the API on the `free`
plan (0.1 CPU / 512 MB). PaddleOCR cannot fit there, so only PyMuPDF runs
in-process: digital PDFs are extracted normally and scanned pages are reported
as unsupported. Recognising scans there needs a plan with more memory.

1. Render Dashboard → **New → Blueprint** → pick this repository. CORS and CSRF
   already point at `https://layout-preserving-ocr.vercel.app`.
2. Rebuild the **frontend** (Vercel) with `VITE_API_BASE_URL` set to the API
   URL (`https://<api-service>.onrender.com`), then redeploy so the bundle picks
   it up. `frontend/.env.production` already carries the deployed API URL, so a
   plain redeploy is enough unless you override it in the Vercel dashboard.
   `frontend/vercel.json` adds the SPA rewrite that keeps `/document/<id>`
   working on a hard refresh.

Free-plan caveats, all of which apply to this app:

- The service spins down after 15 idle minutes; the next request waits ~1 min.
- The disk is ephemeral, so uploads and `db.sqlite3` are lost on every redeploy,
  restart or spin-down. The app is a demo, not storage.
- Extraction runs in a background thread, so a spin-down mid-job loses that job.
- `DJANGO_SERVE_MEDIA=True` is set because there is no separate file host. The
  `/media/` route is explicit in `backend/urls.py` since Django's `static()`
  helper is a no-op when `DEBUG=False`.

Verify after deploy:

```bash
curl https://<api-service>.onrender.com/api/health/
# {"status": "ok", "ocr_backend": "none", "ocr_ready": false}
```

Then upload a digital PDF: layout, editing and export all work. `ocr_backend`
reports `none` and `ocr_ready` stays `false` because PaddleOCR is not installed
on this plan; the service is still healthy and still serves digital PDFs.

## API overview

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health/` | Liveness probe; reports the active OCR backend |
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
