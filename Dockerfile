# ── Stage 1: Build React frontend ────────────────────────────────────────────
FROM node:18-alpine AS frontend-builder

WORKDIR /build/frontend

# Install dependencies first (layer-cache friendly)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund

# Copy source and build
COPY frontend/ ./
RUN npm run build
# Output: /build/frontend/dist


# ── Stage 2: Run FastAPI backend ──────────────────────────────────────────────
FROM python:3.11-slim

# System dependencies required by pytesseract / pdfplumber
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Repo layout inside the image:
#   /app/
#   ├── backend/          ← FastAPI source
#   └── frontend/
#       └── dist/         ← compiled React assets (served by FastAPI)
#
# PROJECT_ROOT in config.py resolves to parents[3] of
# /app/backend/app/core/config.py  →  /app  ✓

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy compiled frontend assets from stage 1
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# Create runtime directories
RUN mkdir -p data/fotos_medidores

# Run the app from the backend directory so `app.main` resolves correctly
WORKDIR /app/backend

ENV PORT=8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
