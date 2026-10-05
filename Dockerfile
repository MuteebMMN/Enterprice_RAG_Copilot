FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    HR_DB_PATH=/app/storage/hr.db \
    APP_DB_PATH=/app/storage/app.db \
    AUDIT_DB_PATH=/app/storage/audit.db \
    UPLOAD_DIR=/app/storage/uploads

WORKDIR /app

# Dependencies first so they are cached until requirements.txt changes
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY templates ./templates
COPY static ./static
COPY data/sample_kb ./data/sample_kb
COPY ingest_sample_kb.py docker-entrypoint.sh ./

# Run as a non-root user. /app/storage holds the databases and uploads (mount a volume here).
RUN sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh \
    && useradd --create-home app \
    && mkdir -p /app/storage \
    && chown -R app:app /app/storage
USER app

VOLUME ["/app/storage"]
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/login' % os.environ.get('PORT','8080'))"

ENTRYPOINT ["./docker-entrypoint.sh"]
