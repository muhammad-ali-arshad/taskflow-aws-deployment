FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 taskflow \
    && useradd --uid 10001 --gid taskflow --no-create-home taskflow

COPY application.py config.py ./
COPY taskflow/ ./taskflow/

USER taskflow
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)" || exit 1

CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "application:application"]
