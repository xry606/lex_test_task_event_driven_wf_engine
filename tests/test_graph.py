from __future__ import annotations

import pytest

from app.graph import validate_workflow
from app.models import DAGDefinition, NodeDefinition, WorkflowDefinition


def _workflow_from_nodes(nodes):
    return WorkflowDefinition(name="test", dag=DAGDefinition(nodes=nodes))


def test_cycle_detection_rejects_cycle():
    nodes = [
        NodeDefinition(id="a", handler="input", dependencies=["c"]),
        NodeDefinition(id="b", handler="call_external_service", dependencies=["a"]),
        NodeDefinition(id="c", handler="call_external_service", dependencies=["b"]),
    ]
    workflow = _workflow_from_nodes(nodes)
    with pytest.raises(ValueError):
        validate_workflow(workflow)


def test_missing_dependency_rejected():
    nodes = [
        NodeDefinition(id="a", handler="input", dependencies=[]),
        NodeDefinition(
            id="b", handler="call_external_service", dependencies=["missing"]
        ),
    ]
    workflow = _workflow_from_nodes(nodes)
    with pytest.raises(ValueError):
        validate_workflow(workflow)
