# backend/Dockerfile — Main service (Agents 1-4 + /prescription endpoint)
#
# Build from the PROJECT ROOT (not from backend/):
#   docker build -f backend/Dockerfile -t medication-companion .
#
# The data/ directory lives at the project root and must be included in the
# build context. This is why the build context must be the project root.

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cache-friendly layer)
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Copy drug lookup CSV — needed by drug_lookup.py and combo_splitter.py
COPY data/ data/

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
