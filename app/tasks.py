from __future__ import annotations

from typing import Any

from app import state
from app.celery_app import celery_app
from app.graph import validate_workflow
from app.handlers import execute_handler
from app.models import NodeStatus
from app.orchestrator import on_node_failure, on_node_success


@celery_app.task(name="app.tasks.execute_node")
def execute_node(
    execution_id: str, node_id: str, handler: str, config: dict[str, Any]
) -> dict[str, Any]:
    definition = state.get_workflow_definition(execution_id)
    if not definition:
        return {}
    graph = validate_workflow(definition)

    current_status = state.get_node_status(execution_id, node_id)
    if current_status == NodeStatus.COMPLETED:
        output = state.get_node_output(execution_id, node_id) or {}
        return output
    if current_status == NodeStatus.FAILED:
        return {}

    try:
        output = execute_handler(execution_id, node_id, handler, config, graph)
        on_node_success(execution_id, node_id, output, graph)
        return output
    except Exception as exc:  # pragma: no cover - defensive
        on_node_failure(execution_id, node_id, str(exc))
        return {}
