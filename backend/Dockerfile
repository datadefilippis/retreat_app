# ── AFianco — Backend Dockerfile ──────────────────────
# Multi-stage: install deps in builder, copy to slim runtime image.
# Final image ~250 MB (Python slim + deps + app code, no dev tools).

# ── Stage 1: dependency installer ────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /install

# System deps for building native wheels (bcrypt, cryptography, numpy)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.prod.txt .

RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.prod.txt


# ── Stage 2: runtime ─────────────────────────────────────────────
FROM python:3.12-slim

# Labels
LABEL maintainer="AFianco" \
      description="FastAPI backend for business monitoring platform"

# Non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install/deps /usr/local

# Copy application code
COPY . .

# Remove files not needed in production
RUN rm -rf venv/ __pycache__/ tests/ backend_test.py .env \
    requirements.txt *.pyc .DS_Store

# Create uploads directory (will be mounted as volume in production)
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app

# Switch to non-root
USER appuser

# Expose port
EXPOSE 8000

# Health check — uses the existing /api/health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# ── Entrypoint ───────────────────────────────────────────────────
# Single worker with gunicorn managing the uvicorn worker class.
# IMPORTANT: --workers 1 because the background job (asyncio.Task in lifespan)
# would run duplicated in each worker. If you need >1 worker, the background
# job must be extracted to a separate process first.
CMD ["gunicorn", "server:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "1", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
