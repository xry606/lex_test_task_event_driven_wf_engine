from __future__ import annotations

import json
from typing import Any
import redis

from app.config import settings
from app.models import NodeStatus, WorkflowDefinition, WorkflowStatus


_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def workflow_definition_key(execution_id: str) -> str:
    return f"wf:{execution_id}:definition"


def workflow_status_key(execution_id: str) -> str:
    return f"wf:{execution_id}:status"


def node_status_key(execution_id: str, node_id: str) -> str:
    return f"wf:{execution_id}:node:{node_id}:status"


def node_output_key(execution_id: str, node_id: str) -> str:
    return f"wf:{execution_id}:node:{node_id}:output"


def dispatch_lock_key(execution_id: str, node_id: str) -> str:
    return f"wf:{execution_id}:node:{node_id}:lock"


def errors_key(execution_id: str) -> str:
    return f"wf:{execution_id}:errors"


def params_key(execution_id: str) -> str:
    return f"wf:{execution_id}:params"


def set_workflow_definition(execution_id: str, definition: WorkflowDefinition) -> None:
    redis_client = get_redis()
    redis_client.set(
        workflow_definition_key(execution_id), definition.model_dump_json()
    )


def get_workflow_definition(execution_id: str) -> WorkflowDefinition | None:
    redis_client = get_redis()
    raw = redis_client.get(workflow_definition_key(execution_id))
    if not raw:
        return None
    return WorkflowDefinition.model_validate_json(raw)


def set_workflow_status(execution_id: str, status: WorkflowStatus) -> None:
    get_redis().set(workflow_status_key(execution_id), status.value)


def get_workflow_status(execution_id: str) -> WorkflowStatus | None:
    raw = get_redis().get(workflow_status_key(execution_id))
    return WorkflowStatus(raw) if raw else None


def set_node_status(execution_id: str, node_id: str, status: NodeStatus) -> None:
    get_redis().set(node_status_key(execution_id, node_id), status.value)


def get_node_status(execution_id: str, node_id: str) -> NodeStatus | None:
    raw = get_redis().get(node_status_key(execution_id, node_id))
    return NodeStatus(raw) if raw else None


def init_workflow_state(
    execution_id: str, definition: WorkflowDefinition, params: dict[str, Any]
) -> None:
    redis_client = get_redis()
    pipe = redis_client.pipeline()
    pipe.set(workflow_status_key(execution_id), WorkflowStatus.RUNNING.value)
    pipe.set(params_key(execution_id), json.dumps(params))
    for node in definition.dag.nodes:
        pipe.set(node_status_key(execution_id, node.id), NodeStatus.PENDING.value)
        pipe.delete(node_output_key(execution_id, node.id))
        pipe.delete(dispatch_lock_key(execution_id, node.id))
    pipe.delete(errors_key(execution_id))
    pipe.execute()


def get_params(execution_id: str) -> dict[str, Any]:
    raw = get_redis().get(params_key(execution_id))
    if not raw:
        return {}
    return json.loads(raw)


def store_node_output(execution_id: str, node_id: str, output: dict[str, Any]) -> None:
    get_redis().set(node_output_key(execution_id, node_id), json.dumps(output))


def get_node_output(execution_id: str, node_id: str) -> dict[str, Any] | None:
    raw = get_redis().get(node_output_key(execution_id, node_id))
    if not raw:
        return None
    return json.loads(raw)


def record_error(execution_id: str, message: str) -> None:
    get_redis().set(errors_key(execution_id), message)


def get_error(execution_id: str) -> str | None:
    return get_redis().get(errors_key(execution_id))


def acquire_dispatch_lock(
    execution_id: str, node_id: str, ttl_seconds: int = 60
) -> bool:
    # Ensures a node is dispatched only once.
    return bool(
        get_redis().set(
            dispatch_lock_key(execution_id, node_id), "1", nx=True, ex=ttl_seconds
        )
    )


def list_node_statuses(
    execution_id: str, definition: WorkflowDefinition
) -> dict[str, NodeStatus]:
    redis_client = get_redis()
    pipe = redis_client.pipeline()
    for node in definition.dag.nodes:
        pipe.get(node_status_key(execution_id, node.id))
    raw_statuses = pipe.execute()
    return {
        node.id: NodeStatus(raw) if raw else NodeStatus.PENDING
        for node, raw in zip(definition.dag.nodes, raw_statuses)
    }


def get_all_outputs(
    execution_id: str, definition: WorkflowDefinition
) -> dict[str, Any]:
    redis_client = get_redis()
    pipe = redis_client.pipeline()
    for node in definition.dag.nodes:
        pipe.get(node_output_key(execution_id, node.id))
    raw_outputs = pipe.execute()
    outputs: dict[str, Any] = {}
    for node, raw in zip(definition.dag.nodes, raw_outputs):
        if raw:
            outputs[node.id] = json.loads(raw)
    return outputs
