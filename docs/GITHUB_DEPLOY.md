# GitHub Deployment Guide

This document explains the CI steps added and the secrets required to build and publish images from GitHub Actions.

What was added

- A workflow at `.github/workflows/ci-build-push.yml` that builds and pushes `helix-frontend` and `helix-backend` images to GitHub Container Registry (`ghcr.io`) on pushes to `main`.

Required repository secrets

- `GITHUB_TOKEN` (provided automatically by Actions) — used to authenticate to GHCR. Ensure the token has `packages: write` permission in repository settings if restricted.
- `AZURE_OPENAI_API_KEY` — backend AI key (do NOT commit this to the repo).
- `ANTHROPIC_API_KEY` — optional.
- `JWT_SECRET` — application JWT secret.
- `DATABASE_URL`, `REDIS_URL`, `MONGO_URL` — runtime database/redis/mongo connection strings for deployment.

Next steps

1. Choose a hosting provider for runtime (Azure App Service, Render, Fly, DigitalOcean, or a Kubernetes cluster).
2. Add a deployment workflow (or provider integration) that pulls the published images from GHCR and deploys them.
3. Consider caching large Python wheels or using a prebuilt base image to avoid long builds for heavy ML dependencies like `torch`.

Kubernetes deployment

- Manifests live under `k8s/` and include:
  - `k8s/namespace.yaml`
  - `k8s/data-services.yaml`
  - `k8s/backend.yaml`
  - `k8s/frontend.yaml`
- The CI workflow now includes a `deploy-to-k8s` job in `.github/workflows/ci-build-push.yml`.
- Required GitHub secrets for Kubernetes deploy:
  - `KUBE_CONFIG_DATA` — base64-encoded kubeconfig for the target cluster.
  - `GHCR_USERNAME` — GitHub registry username (usually your GitHub login).
  - `GHCR_PAT` — personal access token with `read:packages` scope so the cluster can pull GHCR images.
  - `GHCR_EMAIL` — a valid email address used for the image pull secret.
- Required app secrets for backend runtime:
  - `JWT_SECRET`
  - `AZURE_OPENAI_ENDPOINT`
  - `AZURE_OPENAI_API_KEY`
  - `AZURE_OPENAI_DEPLOYMENT`
  - `AZURE_OPENAI_API_VERSION`
  - `ANTHROPIC_API_KEY` (optional)

To deploy:

1. Add the Kubernetes secrets to GitHub.
2. Push to `main`.
3. The workflow will build and push Docker images, then apply the manifests to your cluster.

Verification

- The deploy job now checks rollout status and runs `kubectl get all`, `kubectl get svc`, and `kubectl get pods -o wide` in the target namespace.
- If your cluster does not expose a `LoadBalancer` IP, use port forwarding locally:
  - `kubectl -n helix port-forward svc/frontend 8080:80`
  - then open `http://localhost:8080`
- To inspect runtime health manually:
  - `kubectl -n helix get pods`
  - `kubectl -n helix logs deployment/helix-backend`
  - `kubectl -n helix describe svc frontend`

Build optimization

- The backend Dockerfile now uses a multi-stage build.
- It caches pip packages using BuildKit mount cache and upgrades pip/setuptools/wheel before installing requirements.
- The GitHub Actions workflow now uses registry cache layers for both frontend and backend image builds.
