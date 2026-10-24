FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/app \
    PADDLE_PDX_CACHE_HOME=/app/.paddlex

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/backend/media /app/backend/staticfiles \
    && DJANGO_SECRET_KEY=build-only python backend/manage.py collectstatic --noinput \
    && DJANGO_SECRET_KEY=build-only python -c "import os, sys; sys.path.insert(0, 'backend'); os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings'); import django; django.setup(); from documents.paddleocr_engine import get_ocr_engine; get_ocr_engine()" \
    && chown -R 1000:1000 /app

USER 1000

EXPOSE 7860

CMD ["sh", "-c", "python backend/manage.py migrate --noinput && gunicorn --chdir backend backend.wsgi --bind 0.0.0.0:7860 --workers 1 --threads 8 --timeout 300 --log-file -"]
