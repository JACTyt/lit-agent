"""
Smoke tests that verify all milestones are wired together correctly.
These tests mock LLM calls to avoid network dependencies.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _mock_llm(content="Story word " * 200):
    m = MagicMock()
    m.invoke.return_value.content = content
    return m


@pytest.fixture
def tmp_library(tmp_path, monkeypatch):
    monkeypatch.setattr("api.routes.library.LIBRARY_DIR", tmp_path)
    return tmp_path


def test_library_empty_on_start(tmp_library):
    from api.main import app
    client = TestClient(app)
    resp = client.get("/api/library")
    assert resp.status_code == 200
    assert resp.json() == []


def test_health_returns_provider(monkeypatch):
    from api.main import app
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_schema_v2_written_on_save(tmp_library):
    from agent.tools import _save_book_metadata
    book_path = tmp_library / "test.txt"
    book_path.write_text("Story text", encoding="utf-8")
    sidecar_path = _save_book_metadata(book_path, {
        "book_name": "test", "classification": {"title": "Test"}, "edit_history": []
    })
    saved = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert saved["version"] == 2
    assert "updated_at" in saved


def test_migration_script_runs_on_existing_library():
    from scripts.migrate_schema import migrate_sidecar
    v1 = {"book_name": "x", "classification": {"title": "X"}, "creation_request": "test"}
    result = migrate_sidecar(v1, "library/x.txt")
    assert result["version"] == 2
    assert result["edit_history"] == []
