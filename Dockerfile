FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
ENV PORT=8080

# If your Flask app is exposed as `app` in app.py:
CMD exec gunicorn -w 2 -k gthread -b 0.0.0.0:${PORT} app:app --timeout 120
