import json, pytest
from pathlib import Path
from scripts.migrate_schema import migrate_sidecar, run

def test_migrate_v1_to_v2(tmp_path):
    v1 = {
        "book_name": "test_book",
        "source_path": "library/test_book.txt",
        "creation_request": "a test story",
        "classification": {"title": "Test", "genre": "fable", "theme": "friendship",
                           "audience": "children", "reading_level": "easy", "moral": "be kind"},
        "story_preview": "Once upon a time..."
    }
    result = migrate_sidecar(v1, "library/test_book.txt")
    assert result["version"] == 2
    assert "created_at" in result
    assert "updated_at" in result
    assert result["edit_history"] == []
    assert result["classification"] == v1["classification"]
    assert result["pipeline"] == {}
    assert result["characters_path"] is None

def test_migrate_idempotent(tmp_path):
    v2 = {"version": 2, "book_name": "x", "source_path": "library/x.txt",
          "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
          "classification": {}, "pipeline": {}, "analysis": {}, "edit_history": [],
          "characters_path": None}
    result = migrate_sidecar(v2, "library/x.txt")
    assert result is v2  # same object returned unchanged

def test_run_migrates_files(tmp_path):
    lib = tmp_path / "library"
    lib.mkdir()
    (lib / "story.txt").write_text("text", encoding="utf-8")
    sidecar = lib / "story.metadata.json"
    sidecar.write_text(json.dumps({
        "book_name": "story", "source_path": str(lib / "story.txt"),
        "classification": {"title": "Story"}, "creation_request": "x"
    }), encoding="utf-8")
    count = run(str(lib))
    assert count == 1
    result = json.loads(sidecar.read_text(encoding="utf-8"))
    assert result["version"] == 2
