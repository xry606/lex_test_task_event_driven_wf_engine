# Design Notes

## Overview
The orchestrator validates workflow DAGs, persists definitions/state in Redis, dispatches ready nodes to Celery workers, and responds to node completion events to advance downstream work. Redis is the single source of truth for workflow/node state, outputs, and idempotency locks so multiple API/worker instances can coordinate safely.

## Key Decisions
- **Redis schema**: Keys follow `wf:{execution_id}:*` for definition, workflow status, per-node status/output, dispatch locks, trigger params, and errors. Storing definitions enables workers to reconstruct the graph to evaluate parents for `output` aggregation.
- **Readiness detection**: Parents map + in-degree are precomputed in `WorkflowGraph`. A node is ready when its status is `PENDING` and all parents are `COMPLETED`. Roots are dispatched immediately on trigger.
- **Fan-in correctness**: `dispatch_node_once` uses a Redis `SET NX` lock per `(execution_id,node_id)` to ensure only one dispatch even if multiple parents finish concurrently. Locks expire automatically.
- **Idempotency**: Workers first check node status/output. If already `COMPLETED`, the cached output is returned and no work is re-run. This keeps double-delivered Celery messages safe.
- **Template resolution**: Node configs are resolved before dispatch using `{{ node_id.key }}` or nested variants and `{{ params.x }}`. Missing data raises an error, failing the node and workflow deterministically.
- **Failure handling**: Any node failure marks the workflow `FAILED` and records the error. Further dispatching is stopped via the status guard in `dispatch_node_once`.
- **Mock handlers**: `call_external_service` and `llm_generate` simulate latency with 1–2s sleeps; `input` echoes trigger params; `output` fans in parent outputs into a final payload.
- **Testing & coverage**: Pytest suite covers DAG validation, orchestration fan-in/idempotency, template resolution, API create/trigger/results, handler mocks, and task caching/failure. Coverage reports can be generated with `pytest --cov=app --cov-report=html`.

## Trade-offs
- **Single Redis backend** keeps coordination simple but introduces a SPOF; in production we would use Redis Cluster or managed HA.
- **Graph reconstruction per task** is acceptable for small DAGs; caching or embedding minimal task metadata in Celery payloads could reduce Redis lookups.
- **Co-located API + orchestrator** simplifies deployment. A dedicated orchestrator service subscribed to worker events would scale better for very large workflows.
- **Template language** is intentionally minimal to avoid sandboxing issues; Jinja2 could offer more power with tighter constraints.

## Extensibility
- Add more handlers that stream progress or call real services.
- Emit events (e.g., to Kafka) on state transitions for observability.
- Enforce TTLs/heartbeats for long-running tasks and retries with backoff.
- Add optimistic locking on node status to protect against manual modifications.
