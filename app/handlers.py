from __future__ import annotations

import random
import time
from typing import Any

from app import state


def execute_handler(
    execution_id: str, node_id: str, handler: str, config: dict[str, Any], graph
) -> dict[str, Any]:
    """Dispatch node handlers; kept minimal for mocking."""
    if handler == "input":
        params = state.get_params(execution_id)
        return params
    if handler == "call_external_service":
        return _mock_external_call(config)
    if handler == "llm_generate":
        prompt = config.get("prompt", "")
        time.sleep(random.uniform(1, 2))
        return {"text": f"mock_response: {prompt}"}
    if handler == "output":
        parent_outputs = {
            pid: state.get_node_output(execution_id, pid)
            for pid in graph.parents.get(node_id, [])
        }
        return {"final": parent_outputs}
    raise ValueError(f"Unknown handler: {handler}")


def _mock_external_call(config: dict[str, Any]) -> dict[str, Any]:
    url = config.get("url", "http://example.com/mock")
    time.sleep(random.uniform(1, 2))
    return {
        "url": url,
        "status": "ok",
        "data": {"mock": True, "timestamp": time.time()},
    }
