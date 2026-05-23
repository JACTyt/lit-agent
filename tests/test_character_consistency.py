import json, pytest
from pathlib import Path
from unittest.mock import MagicMock


def _mock_llm(content):
    m = MagicMock()
    m.invoke.return_value.content = content
    return m


def test_write_characters_json(tmp_path):
    from agent.tools import _write_characters_json
    book_path = tmp_path / "story.txt"
    book_path.write_text("text", encoding="utf-8")
    char_data = {
        "version": 1, "story": "story",
        "extracted_at": "2026-01-01T00:00:00Z",
        "world": {"setting": "forest", "time_period": "medieval", "tone": "dark"},
        "characters": [{"name": "Aria", "role": "protagonist", "traits": ["brave"],
                        "arc": "learns trust", "first_appears": "paragraph 1"}]
    }
    path = _write_characters_json(book_path, char_data)
    assert path.exists()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["characters"][0]["name"] == "Aria"


def test_build_character_card():
    from agent.tools import _build_character_card
    char_data = {
        "world": {"setting": "Lantern Vale", "time_period": "pre-industrial", "tone": "warm"},
        "characters": [
            {"name": "Mira", "role": "protagonist", "traits": ["observant", "fearful"],
             "arc": "learns to act", "first_appears": "p1"}
        ]
    }
    card = _build_character_card(char_data)
    assert "Mira" in card
    assert "protagonist" in card
    assert "Lantern Vale" in card


def test_edit_book_injects_characters(tmp_path, monkeypatch):
    from agent import tools as t
    monkeypatch.setattr(t, "LIBRARY_DIR", tmp_path)
    book = tmp_path / "hero.txt"
    book.write_text("Title: Hero\nGenre: fable\n\nStory:\nOnce upon a time.", encoding="utf-8")
    char_data = {
        "world": {"setting": "Valley", "time_period": "ancient", "tone": "epic"},
        "characters": [{"name": "Hero", "role": "protagonist", "traits": ["brave"],
                        "arc": "grows", "first_appears": "p1"}]
    }
    (tmp_path / "hero.characters.json").write_text(
        json.dumps(char_data), encoding="utf-8"
    )
    captured = {}
    def mock_call_llm(prompt, temperature=0.7):
        captured["prompt"] = prompt
        return "Revised story text " * 50
    monkeypatch.setattr(t, "_call_llm", mock_call_llm)
    t.edit_book.func("hero", "make it sadder")
    assert "Hero" in captured["prompt"]
    assert "Character roster" in captured["prompt"]
