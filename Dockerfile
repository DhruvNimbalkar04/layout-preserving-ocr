FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN DJANGO_SECRET_KEY=build-only-key python backend/manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python backend/manage.py migrate && gunicorn --chdir backend backend.wsgi --bind 0.0.0.0:${PORT:-8000} --log-file -"]
