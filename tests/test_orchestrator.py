from __future__ import annotations

import pytest

from app import state
from app.graph import validate_workflow
from app.models import DAGDefinition, NodeDefinition, WorkflowDefinition
from app.orchestrator import (
    dispatch_node_once,
    start_workflow,
    on_node_success,
)
from app.utils import resolve_templates


def sample_workflow() -> WorkflowDefinition:
    nodes = [
        NodeDefinition(id="input", handler="input", dependencies=[]),
        NodeDefinition(id="b", handler="call_external_service", dependencies=["input"]),
        NodeDefinition(id="c", handler="call_external_service", dependencies=["input"]),
        NodeDefinition(id="d", handler="output", dependencies=["b", "c"]),
    ]
    return WorkflowDefinition(name="fan_in", dag=DAGDefinition(nodes=nodes))


def test_fan_in_dispatch_order(monkeypatch):
    workflow = sample_workflow()
    graph = validate_workflow(workflow)
    execution_id = "exec-1"
    state.set_workflow_definition(execution_id, workflow)

    dispatched: list[str] = []

    def fake_send_task(name, args, kwargs=None):  # noqa: ANN001
        node = args[1]
        dispatched.append(node)

    monkeypatch.setattr(
        "app.orchestrator.celery_app",
        type("obj", (), {"send_task": staticmethod(fake_send_task)}),
    )

    start_workflow(execution_id, workflow, graph, params={})
    assert dispatched == ["input"]

    on_node_success(execution_id, "input", {}, graph)
    assert set(dispatched) == {"input", "b", "c"}

    on_node_success(execution_id, "b", {"ok": True}, graph)
    assert "d" not in dispatched

    on_node_success(execution_id, "c", {"ok": True}, graph)
    assert "d" in dispatched
    assert dispatched.count("d") == 1


def test_dispatch_node_once_is_idempotent(monkeypatch):
    workflow = sample_workflow()
    graph = validate_workflow(workflow)
    execution_id = "exec-2"
    state.set_workflow_definition(execution_id, workflow)
    state.init_workflow_state(execution_id, workflow, {})

    calls: list[str] = []

    def fake_send_task(name, args, kwargs=None):  # noqa: ANN001
        calls.append(args[1])

    monkeypatch.setattr(
        "app.orchestrator.celery_app",
        type("obj", (), {"send_task": staticmethod(fake_send_task)}),
    )

    assert dispatch_node_once(execution_id, "input", graph) is True
    assert dispatch_node_once(execution_id, "input", graph) is False
    assert calls.count("input") == 1


def test_template_resolution_success_and_failure():
    context = {"a": {"value": {"nested": 5}}, "params": {"threshold": 2}}
    config = {"field": "{{ a.value.nested }}", "other": "x{{ params.threshold }}y"}
    resolved = resolve_templates(config, context)
    assert resolved["field"] == 5
    assert resolved["other"] == "x2y"

    with pytest.raises(ValueError):
        resolve_templates({"missing": "{{ no.key }}"}, context)
