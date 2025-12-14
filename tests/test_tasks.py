from __future__ import annotations


from app import state
from app.models import DAGDefinition, NodeDefinition, WorkflowDefinition, NodeStatus
from app.tasks import execute_node


def sample_workflow() -> WorkflowDefinition:
    nodes = [
        NodeDefinition(id="input", handler="input", dependencies=[]),
        NodeDefinition(id="output", handler="output", dependencies=["input"]),
    ]
    return WorkflowDefinition(name="tasks_test", dag=DAGDefinition(nodes=nodes))


def test_execute_node_returns_cached_output(monkeypatch):
    wf = sample_workflow()
    execution_id = "task-exec"
    state.set_workflow_definition(execution_id, wf)
    state.set_node_status(execution_id, "input", NodeStatus.COMPLETED)
    state.store_node_output(execution_id, "input", {"foo": "bar"})

    called = {}
    monkeypatch.setattr(
        "app.tasks.execute_handler",
        lambda *args, **kwargs: called.update({"called": True}),
    )

    output = execute_node(execution_id, "input", "input", {})
    assert output == {"foo": "bar"}
    assert called == {}


def test_execute_node_failure_marks_failed(monkeypatch):
    wf = sample_workflow()
    execution_id = "task-fail"
    state.set_workflow_definition(execution_id, wf)
    state.set_node_status(execution_id, "input", NodeStatus.PENDING)

    def boom(*_, **__):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.tasks.execute_handler", boom)

    result = execute_node(execution_id, "input", "input", {})
    assert result == {}
    assert state.get_node_status(execution_id, "input") == NodeStatus.FAILED
