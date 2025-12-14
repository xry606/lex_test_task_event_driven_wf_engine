from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import state  # noqa: E402


class FakePipeline:
    def __init__(self, store: dict):
        self.store = store
        self.commands = []

    def set(self, key, value, nx=False, ex=None):  # noqa: ANN001
        if nx and key in self.store:
            self.commands.append(False)
            return self
        self.store[key] = value
        self.commands.append(True)
        return self

    def delete(self, key):  # noqa: ANN001
        self.store.pop(key, None)
        self.commands.append(True)
        return self

    def get(self, key):  # noqa: ANN001
        value = self.store.get(key)
        self.commands.append(value)
        return self

    def execute(self):
        output = list(self.commands)
        self.commands = []
        return output


class FakeRedis:
    def __init__(self):
        self.store = {}

    def set(self, key, value, nx=False, ex=None):  # noqa: ANN001
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def get(self, key):  # noqa: ANN001
        return self.store.get(key)

    def delete(self, key):  # noqa: ANN001
        self.store.pop(key, None)

    def pipeline(self):
        return FakePipeline(self.store)


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    client = FakeRedis()
    state._redis_client = client
    yield client
