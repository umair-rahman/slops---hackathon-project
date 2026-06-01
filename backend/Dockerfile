FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (production only)
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e "." && \
    python -m spacy download en_core_web_sm

# Pre-download embedding model to bake into image
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy source
COPY src/ ./src/

EXPOSE 8000

CMD ["uvicorn", "marginalia.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
