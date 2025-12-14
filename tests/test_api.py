from __future__ import annotations

from fastapi.testclient import TestClient

from app import state
from app.main import app
from app.models import DAGDefinition, NodeDefinition, WorkflowDefinition, WorkflowStatus


def sample_workflow() -> WorkflowDefinition:
    nodes = [
        NodeDefinition(id="input", handler="input", dependencies=[]),
        NodeDefinition(id="output", handler="output", dependencies=["input"]),
    ]
    return WorkflowDefinition(name="api_test", dag=DAGDefinition(nodes=nodes))


def test_create_and_trigger_workflow(monkeypatch):
    client = TestClient(app)
    wf = sample_workflow()

    # Create workflow
    response = client.post("/workflows", json=wf.model_dump())
    assert response.status_code == 200
    execution_id = response.json()["execution_id"]
    assert state.get_workflow_status(execution_id) == WorkflowStatus.PENDING

    triggered = {}

    def fake_start(exec_id, definition, graph, params):
        triggered["id"] = exec_id
        triggered["params"] = params

    monkeypatch.setattr("app.main.start_workflow", fake_start)

    trigger_resp = client.post(
        f"/workflows/{execution_id}/trigger", json={"params": {"x": 1}}
    )
    assert trigger_resp.status_code == 200
    assert triggered["id"] == execution_id
    assert triggered["params"] == {"x": 1}


def test_results_endpoint_reflects_state():
    client = TestClient(app)
    wf = sample_workflow()
    response = client.post("/workflows", json=wf.model_dump())
    execution_id = response.json()["execution_id"]

    state.set_workflow_status(execution_id, WorkflowStatus.COMPLETED)
    state.store_node_output(execution_id, "input", {"hello": "world"})
    state.store_node_output(
        execution_id, "output", {"final": {"input": {"hello": "world"}}}
    )

    res = client.get(f"/workflows/{execution_id}/results")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["results"]["input"] == {"hello": "world"}
