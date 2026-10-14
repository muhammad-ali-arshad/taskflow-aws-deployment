FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/taskflow.db

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 taskflow \
    && useradd --uid 10001 --gid taskflow --no-create-home taskflow \
    && mkdir /data \
    && chown taskflow:taskflow /data

COPY application.py config.py ./
COPY taskflow/ ./taskflow/

USER taskflow
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)" || exit 1

# One worker avoids concurrent SQLite schema creation on the first launch.
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "application:application"]
