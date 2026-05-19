"""Celery application for heavy Helix jobs.

Run from `helix-backend/`:

  celery -A celery_app worker --loglevel=info

Set `HELIX_USE_CELERY=1` in the API environment to enqueue tasks instead of
in-process BackgroundTasks.
"""
from __future__ import annotations

import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

_redis = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "helix",
    broker=_redis,
    backend=_redis,
)


@celery_app.task(name="helix.generate_artifacts")
def generate_artifacts_task(project_id: str, user_id: int, task_id: str) -> None:
    from app.services.generation_service import generate_artifacts_blocking

    generate_artifacts_blocking(project_id, user_id, task_id)


@celery_app.task(name="helix.generate_testcases")
def generate_testcases_task(project_id: str, user_id: int, task_id: str) -> None:
    from app.services.generation_service import generate_testcases_blocking

    generate_testcases_blocking(project_id, user_id, task_id)
