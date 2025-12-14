from __future__ import annotations

import logging
from typing import Any

from app import state
from app.celery_app import celery_app
from app.graph import WorkflowGraph
from app.models import NodeStatus, WorkflowDefinition, WorkflowStatus
from app.utils import resolve_templates

logger = logging.getLogger(__name__)


def dispatch_node_once(execution_id: str, node_id: str, graph: WorkflowGraph) -> bool:
    if state.get_workflow_status(execution_id) == WorkflowStatus.FAILED:
        return False
    if not state.acquire_dispatch_lock(execution_id, node_id):
        return False

    current_status = state.get_node_status(execution_id, node_id)
    if current_status in {NodeStatus.RUNNING, NodeStatus.COMPLETED}:
        return False

    definition = graph.nodes[node_id]
    parent_outputs = {
        pid: state.get_node_output(execution_id, pid)
        for pid in graph.parents.get(node_id, [])
    }
    params = state.get_params(execution_id)
    context = {**parent_outputs, "params": params}
    try:
        resolved_config = resolve_templates(definition.config, context)
    except ValueError as exc:
        logger.error("Template resolution failed for node %s: %s", node_id, exc)
        fail_workflow(
            execution_id, f"Template resolution failed for node {node_id}: {exc}"
        )
        state.set_node_status(execution_id, node_id, NodeStatus.FAILED)
        return False

    state.set_node_status(execution_id, node_id, NodeStatus.RUNNING)
    logger.info("Dispatching node %s for workflow %s", node_id, execution_id)
    celery_app.send_task(
        "app.tasks.execute_node",
        args=[execution_id, node_id, definition.handler, resolved_config],
    )
    return True


def is_node_ready(execution_id: str, node_id: str, graph: WorkflowGraph) -> bool:
    status_value = state.get_node_status(execution_id, node_id)
    if status_value != NodeStatus.PENDING:
        return False
    parents: list[str] = graph.parents.get(node_id, [])
    return all(
        state.get_node_status(execution_id, pid) == NodeStatus.COMPLETED
        for pid in parents
    )


def start_workflow(
    execution_id: str,
    definition: WorkflowDefinition,
    graph: WorkflowGraph,
    params: dict[str, Any],
) -> None:
    state.init_workflow_state(execution_id, definition, params)
    for node_id in graph.roots:
        dispatch_node_once(execution_id, node_id, graph)


def on_node_success(
    execution_id: str, node_id: str, output: dict[str, Any], graph: WorkflowGraph
) -> None:
    if state.get_workflow_status(execution_id) == WorkflowStatus.FAILED:
        return
    state.store_node_output(execution_id, node_id, output)
    state.set_node_status(execution_id, node_id, NodeStatus.COMPLETED)
    logger.info("Node %s completed for workflow %s", node_id, execution_id)

    # Dispatch downstream nodes that are now ready.
    for child in graph.adjacency.get(node_id, []):
        if is_node_ready(execution_id, child, graph):
            dispatch_node_once(execution_id, child, graph)

    # Check completion
    node_statuses = state.list_node_statuses(
        execution_id, definition=definition_from_graph(graph)
    )
    if all(status == NodeStatus.COMPLETED for status in node_statuses.values()):
        state.set_workflow_status(execution_id, WorkflowStatus.COMPLETED)


def on_node_failure(execution_id: str, node_id: str, error: str) -> None:
    logger.error("Node %s failed for workflow %s: %s", node_id, execution_id, error)
    state.set_node_status(execution_id, node_id, NodeStatus.FAILED)
    fail_workflow(execution_id, error)


def fail_workflow(execution_id: str, error: str) -> None:
    state.record_error(execution_id, error)
    state.set_workflow_status(execution_id, WorkflowStatus.FAILED)


def definition_from_graph(graph: WorkflowGraph) -> WorkflowDefinition:
    return graph.definition
