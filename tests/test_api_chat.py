import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_chat_returns_run_id(monkeypatch):
    mock_agent = MagicMock()
    mock_agent.stream.return_value = [{"messages": [{"content": "Hello!"}]}]
    monkeypatch.setattr("api.routes.chat._get_agent", lambda: mock_agent)
    resp = client.post("/api/chat", json={"message": "hi"})
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert "reply" in data or "status" in data


def test_chat_returns_agent_reply(monkeypatch):
    mock_agent = MagicMock()
    mock_agent.stream.return_value = [
        {"messages": [MagicMock(content="Once upon a time")]}
    ]
    monkeypatch.setattr("api.routes.chat._get_agent", lambda: mock_agent)
    resp = client.post("/api/chat", json={"message": "tell me a story"})
    assert resp.status_code == 200
    body = resp.json()
    assert "run_id" in body
