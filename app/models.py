from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class NodeStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class NodeDefinition(BaseModel):
    id: str = Field(..., pattern=r"^[a-zA-Z0-9_\-]+$")
    handler: str
    dependencies: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("dependencies", mode="before")
    @classmethod
    def ensure_dependencies(cls, value: Any) -> list[str]:
        if value is None:
            return []
        return list(value)


class DAGDefinition(BaseModel):
    nodes: list[NodeDefinition]

    @model_validator(mode="after")
    def ensure_unique_ids(self) -> "DAGDefinition":
        seen = set()
        for node in self.nodes:
            if node.id in seen:
                raise ValueError(f"Duplicate node id detected: {node.id}")
            seen.add(node.id)
        return self


class WorkflowDefinition(BaseModel):
    name: str
    dag: DAGDefinition


class WorkflowCreateResponse(BaseModel):
    execution_id: str
    status: WorkflowStatus


class TriggerRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)


class WorkflowStatusResponse(BaseModel):
    execution_id: str
    status: WorkflowStatus
    node_statuses: dict[str, NodeStatus]


class WorkflowResultResponse(BaseModel):
    execution_id: str
    status: WorkflowStatus
    results: dict[str, Any]
    error: str | None = None
