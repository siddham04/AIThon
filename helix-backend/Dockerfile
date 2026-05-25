# syntax=docker/dockerfile:1
# API-only image for Render (Root Directory = helix-backend, Dockerfile Path = Dockerfile).
# Pair with Vercel for the React UI — see docs/RENDER_SPLIT_DEPLOY.md
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel
RUN --mount=type=cache,target=/root/.cache/pip python -m pip install -r requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip python -m spacy download en_core_web_sm

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
