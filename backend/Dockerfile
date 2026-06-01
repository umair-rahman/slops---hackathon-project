FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e "."

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Pre-download embedding model (baked into image — no cold start delay)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy source code
COPY src/ ./src/

# Render uses PORT env variable
ENV PORT=8000
EXPOSE $PORT

CMD uvicorn marginalia.main:app --host 0.0.0.0 --port $PORT
