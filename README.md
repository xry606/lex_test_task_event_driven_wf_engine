# Event-Driven Workflow Orchestration Engine

FastAPI + Celery + Redis implementation of a DAG-based, event-driven workflow engine with fan-out/fan-in, template-based data passing, and idempotent task execution.

## Quickstart

```bash
docker compose up --build
```

Services:
- API/orchestrator: http://localhost:8000
- Redis: localhost:6379
- Celery worker: runs the node handlers

## Example Workflow

```json
{
  "name": "Parallel API Fetcher",
  "dag": {
    "nodes": [
      {"id": "input", "handler": "input", "dependencies": []},
      {"id": "get_user", "handler": "call_external_service", "dependencies": ["input"], "config": {"url": "http://localhost:8911/document/policy/list"}},
      {"id": "get_posts", "handler": "call_external_service", "dependencies": ["input"], "config": {"url": "http://localhost:8911/document/policy/list"}},
      {"id": "get_comments", "handler": "call_external_service", "dependencies": ["input"], "config": {"url": "http://localhost:8911/document/policy/list"}},
      {"id": "output", "handler": "output", "dependencies": ["get_user", "get_posts", "get_comments"]}
    ]
  }
}
```

## API Usage

1. **Create** a workflow definition:
   ```bash
   curl -X POST http://localhost:8000/workflows -H "Content-Type: application/json" -d @workflow.json
   # -> { "execution_id": "...", "status": "PENDING" }
   ```

2. **Trigger** execution:
   ```bash
   curl -X POST "http://localhost:8000/workflows/<execution_id>/trigger" -H "Content-Type: application/json" -d '{"params": {"user_id": 123}}'
   ```

3. **Check status**:
   ```bash
   curl http://localhost:8000/workflows/<execution_id>
   ```

4. **Fetch results**:
   ```bash
   curl http://localhost:8000/workflows/<execution_id>/results
   ```

## Development

Install dependencies locally:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run API locally:
```bash
uvicorn app.main:app --reload
```

Run worker:
```bash
celery -A app.celery_app.celery_app worker --loglevel=INFO
```

Run tests:
```bash
pytest
```

# open htmlcov/index.html for the detailed report
```
Current suite covers ~90% of the codebase; view the breakdown in `htmlcov/index.html`.

## Project Layout

- `app/main.py` - FastAPI app + HTTP API
- `app/graph.py` - DAG parsing and validation
- `app/orchestrator.py` - readiness detection, dispatch, template resolution
- `app/tasks.py` - Celery task definitions and worker entry
- `app/handlers.py` - handler implementations used by Celery tasks (mocked)
- `app/utils.py` - template resolution helpers
- `app/state.py` - Redis-backed persistence, keys, idempotency locks
- `app/models.py` - Pydantic schemas and enums
- `app/celery_app.py` - Celery configuration (queues/routes)
- `app/config.py` - environment-driven settings
- `docker-compose.yml` - API, worker, Redis (with bind mounts)
- `Dockerfile` - multistage build, non-root runtime
- `tests/` - pytest coverage of validation, orchestration, handlers, tasks, API
