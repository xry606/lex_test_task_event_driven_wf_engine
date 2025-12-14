from __future__ import annotations

from celery import Celery
from kombu import Exchange, Queue

from app.config import settings

broker_url = settings.celery_broker_url
result_backend = settings.celery_result_backend

celery_app = Celery(
    "workflow_engine",
    broker=broker_url,
    backend=result_backend,
    include=["app.tasks"],
)

default_exchange = Exchange("workflow", type="direct")
celery_app.conf.task_default_queue = "workflow"
celery_app.conf.task_default_exchange = default_exchange.name
celery_app.conf.task_default_exchange_type = default_exchange.type
celery_app.conf.task_default_routing_key = "workflow"
celery_app.conf.task_queues = (
    Queue("workflow", exchange=default_exchange, routing_key="workflow"),
)

celery_app.conf.update(
    task_routes={
        "app.tasks.execute_node": {"queue": "workflow", "routing_key": "workflow"}
    },
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
)

celery_app.autodiscover_tasks(["app"])


@celery_app.task
def healthcheck() -> str:
    return "ok"
