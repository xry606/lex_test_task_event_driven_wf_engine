from __future__ import annotations

import os


class Settings:
    """Centralized configuration sourced from environment variables."""

    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", redis_url)
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", celery_broker_url)


settings = Settings()
