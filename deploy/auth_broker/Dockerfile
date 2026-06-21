# Auth broker — thin Cloud Run service (Firebase JWT → GCS → Agent Runtime).
#
# Build from repo root:
#   docker build -f deploy/auth_broker/Dockerfile -t medication-companion-broker .
#
# Run locally:
#   cd backend && uvicorn auth_broker.main:app --reload --port 8080

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

CMD ["uv", "run", "uvicorn", "auth_broker.main:app", "--host", "0.0.0.0", "--port", "8080"]
