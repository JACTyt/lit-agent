import json, pytest
from pathlib import Path
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health(tmp_path, monkeypatch):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "provider" in data

def test_list_library_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("api.routes.library.LIBRARY_DIR", tmp_path)
    resp = client.get("/api/library")
    assert resp.status_code == 200
    assert resp.json() == []

def test_get_book(tmp_path, monkeypatch):
    monkeypatch.setattr("api.routes.library.LIBRARY_DIR", tmp_path)
    (tmp_path / "hero.txt").write_text("Once upon a time", encoding="utf-8")
    resp = client.get("/api/library/hero")
    assert resp.status_code == 200
    assert resp.json()["text"] == "Once upon a time"

def test_get_book_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("api.routes.library.LIBRARY_DIR", tmp_path)
    resp = client.get("/api/library/missing")
    assert resp.status_code == 404
