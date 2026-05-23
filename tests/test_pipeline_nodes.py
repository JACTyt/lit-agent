import pytest
from unittest.mock import MagicMock, patch
from pipeline.state import StoryState


def _mock_llm(content: str):
    m = MagicMock()
    m.invoke.return_value.content = content
    return m


def _base_state(**kwargs) -> StoryState:
    defaults: dict = dict(
        request="a brave knight", params={}, outline={}, draft="",
        critic_score=0.0, critic_feedback="", retry_count=0,
        final_story="", metadata={},
    )
    defaults.update(kwargs)
    return StoryState(**defaults)


def test_planner_populates_outline(monkeypatch):
    outline_json = '{"title":"The Knight","genre":"fantasy","theme":"courage","audience":"general","reading_level":"middle","moral":"be brave","characters":{},"conflict":"a dragon","resolution":"peace","setting":"castle"}'
    monkeypatch.setattr("pipeline.nodes.get_chat_llm", lambda **kw: _mock_llm(outline_json))
    from pipeline.nodes import planner
    result = planner(_base_state())
    assert result["outline"]["title"] == "The Knight"
    assert result["metadata"]["version"] == 2
    assert result["metadata"]["classification"]["genre"] == "fantasy"
    assert "plan" in result["metadata"]["pipeline"]["stages_completed"]


def test_writer_produces_draft(monkeypatch):
    monkeypatch.setattr("pipeline.nodes.get_chat_llm", lambda **kw: _mock_llm("Part text here " * 60))
    from pipeline.nodes import writer
    state = _base_state(outline={"moral": "be brave"}, metadata={"pipeline": {"stages_completed": ["plan"]}, "classification": {}})
    result = writer(state)
    assert len(result["draft"]) > 0
    assert "write" in result["metadata"]["pipeline"]["stages_completed"]


def test_writer_increments_retry_on_feedback(monkeypatch):
    monkeypatch.setattr("pipeline.nodes.get_chat_llm", lambda **kw: _mock_llm("Some text " * 60))
    from pipeline.nodes import writer
    state = _base_state(critic_feedback="Too short.", retry_count=0,
                        outline={}, metadata={"pipeline": {"stages_completed": ["plan", "write"]}, "classification": {}})
    result = writer(state)
    assert result["retry_count"] == 1
