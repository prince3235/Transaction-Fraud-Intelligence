# ─────────────────────────────────────────────────────────────────────────────
# Root Dockerfile — monolithic dev container (runs both API + Streamlit)
# For production, use docker/Dockerfile.api + docker/Dockerfile.streamlit instead.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg2 + scikit-learn + shap
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose ports (API + Streamlit)
EXPOSE 8000 8501

# Drop root
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

# Launch both services via run.py (dev convenience only)
CMD ["python", "run.py"]
