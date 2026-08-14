FROM python:3.11-slim

WORKDIR /app

# System dependencies for PyTorch + causal libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in two stages for Docker layer caching
COPY requirements.txt .

# 1. PyTorch CPU (smaller image — no CUDA)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2. Main requirements (Groq, FastAPI, causal-learn, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p /app/models /app/chroma_db /app/data

# Set Python path for imports
ENV PYTHONPATH=/app

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import httpx; r = httpx.get('http://localhost:8000/api/v1/health', timeout=5); assert r.status_code == 200" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
