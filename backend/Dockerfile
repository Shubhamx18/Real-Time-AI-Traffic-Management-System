# ═══════════════════════════════════════════════════════
# Backend Dockerfile — YOLOv8x Traffic Queue Analyzer
# Python 3.11 + OpenCV + CUDA-ready
# ═══════════════════════════════════════════════════════

FROM python:3.11-slim

# System dependencies for OpenCV (Debian trixie compatible)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0t64 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libfontconfig1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (Docker-optimized)
COPY requirements.docker.txt .
RUN pip install --no-cache-dir -r requirements.docker.txt

# Download YOLOv8x model at build time (avoids download at runtime)
RUN python -c "from ultralytics import YOLO; YOLO('yolov8x.pt')"

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Run server
CMD ["python", "run_server.py"]
