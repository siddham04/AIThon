# syntax=docker/dockerfile:1
# API-only image for Render (Root Directory = helix-backend, Dockerfile Path = Dockerfile).
# Pair with Vercel for the React UI — see docs/RENDER_SPLIT_DEPLOY.md
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Same opt-in heavy-ML-stack pattern as Dockerfile.all-in-one.
# Default = `requirements-render.txt` (slim, Render Free safe).
# Pass `--build-arg REQUIREMENTS_FILE=requirements.txt` for the
# full stack (needs >= 1 GB build RAM, Render Starter or larger).
ARG REQUIREMENTS_FILE=requirements-render.txt
COPY requirements.txt requirements-render.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-cache-dir --prefer-binary -r "${REQUIREMENTS_FILE}"
RUN --mount=type=cache,target=/root/.cache/pip \
    if python -c "import spacy" 2>/dev/null; then \
        python -m spacy download en_core_web_sm ; \
    else \
        echo "[helix] spaCy not installed in this build — skipping en_core_web_sm download (nlp_service falls back to heuristic ambiguity detection)" ; \
    fi

COPY . /app/
RUN chmod +x /app/docker-entrypoint.sh

FROM python:3.11-slim
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

ENV PYTHONPATH=/app
# Render Free tier has 512 MB RAM. Skip sentence-transformers/PyTorch model
# load by default — RAG search returns empty, hackathon demo path is unaffected.
ENV HELIX_DISABLE_EMBEDDINGS=1
ENV HELIX_DEMO_FAST=1
ENV HELIX_HACKATHON_AUTH=1
ENV DATABASE_URL=sqlite:////app/data/helix.db
RUN mkdir -p /app/data
EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
