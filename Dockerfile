FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
COPY agents /app/agents
# Modelos y datos incluidos en el repo (ya no se necesita S3)
COPY data /app/data

ENV PORT=7860
EXPOSE 7860

CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT
