import pytest
from unittest.mock import patch
from pipeline.rubric import score_draft, _word_count, _has_conflict, _has_resolution

def test_word_count():
    assert _word_count("one two three") == 3
    assert _word_count("") == 0

def test_has_conflict():
    assert _has_conflict("There was a great danger in the valley")
    assert not _has_conflict("Everything was fine and peaceful")

def test_has_resolution():
    assert _has_resolution("Finally she overcame her fear")
    assert not _has_resolution("The story begins on a cold morning")

def test_full_score():
    long_draft = ("conflict danger " * 30) + ("resolved finally " * 30) + ("word " * 540)
    outline = {"moral": ""}
    score, feedback = score_draft(long_draft, outline)
    assert score == 0.75  # 3 of 4 criteria (moral skipped when empty)

def test_zero_score_empty_draft():
    score, feedback = score_draft("", {"moral": "kindness wins"})
    assert score == 0.0
    assert "short" in feedback.lower() or "conflict" in feedback.lower()

def test_score_with_moral(monkeypatch):
    from unittest.mock import MagicMock
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = "YES"
    monkeypatch.setattr("pipeline.rubric.get_chat_llm", lambda **kw: mock_llm)
    draft = ("conflict problem " * 30) + ("resolved finally " * 30) + ("word " * 560)
    score, _ = score_draft(draft, {"moral": "kindness wins"})
    assert score == 1.0
