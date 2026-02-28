# Stage 1: Build frontend
FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python application
FROM python:3.12-slim
WORKDIR /app

# System deps: ffmpeg + WeasyPrint libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
  && rm -rf /var/lib/apt/lists/*

# Copy project files and install
COPY pyproject.toml README.md ./
COPY src/ src/

# Copy built frontend into static dir
COPY --from=frontend /src/talekeeper/static/ src/talekeeper/static/

RUN pip install --no-cache-dir .

CMD ["talekeeper", "serve", "--host", "0.0.0.0", "--no-browser"]
