# Trident WebShell Detector v1.7.8
# Multi-stage build for minimal image size

FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .

# Install build dependencies for yara-python compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && pip install --no-cache-dir --user -r requirements.txt \
    && apt-get purge -y --auto-remove gcc g++ libssl-dev libffi-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*

FROM python:3.11-slim

LABEL maintainer="yourusername <yourusername@example.com>"
LABEL version="1.7.8"
LABEL description="Trident WebShell Detector - Cross-platform real-time detection"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create runtime directories
RUN mkdir -p data/sessions logs/Trident logs/Website-PhpStudy \
    && chmod +x install.sh start.sh stop.sh

# Expose admin port
EXPOSE 8080

# Health check (uses the built-in /admin/health endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/v1/health', timeout=5)" || exit 1

# Default: run in foreground (logs to stdout)
CMD ["python", "app.py"]
