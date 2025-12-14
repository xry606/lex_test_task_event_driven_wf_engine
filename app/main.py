from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, HTTPException

from app.graph import validate_workflow
from app import state
from app.models import (
    TriggerRequest,
    WorkflowCreateResponse,
    WorkflowDefinition,
    WorkflowResultResponse,
    WorkflowStatus,
    WorkflowStatusResponse,
)
from app.orchestrator import start_workflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Event-Driven Workflow Engine")


@app.post("/workflows", response_model=WorkflowCreateResponse)
def create_workflow(definition: WorkflowDefinition) -> WorkflowCreateResponse:
    # Validate DAG and persist
    validate_workflow(definition)
    execution_id = str(uuid.uuid4())
    state.set_workflow_definition(execution_id, definition)
    state.set_workflow_status(execution_id, WorkflowStatus.PENDING)
    return WorkflowCreateResponse(
        execution_id=execution_id, status=WorkflowStatus.PENDING
    )


@app.post("/workflows/{execution_id}/trigger")
def trigger_workflow(execution_id: str, request: TriggerRequest) -> dict[str, str]:
    definition = state.get_workflow_definition(execution_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Workflow not found")
    graph = validate_workflow(definition)
    start_workflow(execution_id, definition, graph, request.params)
    return {"execution_id": execution_id, "status": "triggered"}


@app.get("/workflows/{execution_id}", response_model=WorkflowStatusResponse)
def get_workflow_status(execution_id: str) -> WorkflowStatusResponse:
    definition = state.get_workflow_definition(execution_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Workflow not found")
    status_value = state.get_workflow_status(execution_id) or WorkflowStatus.PENDING
    node_statuses = state.list_node_statuses(execution_id, definition)
    return WorkflowStatusResponse(
        execution_id=execution_id, status=status_value, node_statuses=node_statuses
    )


@app.get("/workflows/{execution_id}/results", response_model=WorkflowResultResponse)
def get_workflow_results(execution_id: str) -> WorkflowResultResponse:
    definition = state.get_workflow_definition(execution_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Workflow not found")
    status_value = state.get_workflow_status(execution_id) or WorkflowStatus.PENDING
    outputs = state.get_all_outputs(execution_id, definition)
    error = state.get_error(execution_id)
    return WorkflowResultResponse(
        execution_id=execution_id, status=status_value, results=outputs, error=error
    )
