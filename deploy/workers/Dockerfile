# Prescription worker — Pub/Sub push consumer (Cloud Run).
#
# Build from repo root:
#   docker build -f deploy/workers/Dockerfile -t medication-companion-prescription-worker .

FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY backend ./backend
COPY data ./data
COPY specs ./specs

RUN uv sync --locked --no-dev

ENV PYTHONPATH=/app/backend
ENV PORT=8080

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "workers.prescription_worker:app", "--host", "0.0.0.0", "--port", "8080"]
