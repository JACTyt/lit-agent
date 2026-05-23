import pytest
from unittest.mock import MagicMock, patch


def _mock_llm(content="Story text " * 100):
    m = MagicMock()
    m.invoke.return_value.content = content
    return m


def test_pipeline_returns_final_story(monkeypatch):
    monkeypatch.setattr("pipeline.nodes.get_chat_llm", lambda **kw: _mock_llm())
    monkeypatch.setattr("pipeline.rubric.get_chat_llm", lambda **kw: _mock_llm("YES"))
    from pipeline.graph import build_pipeline
    p = build_pipeline()
    result = p.invoke({
        "request": "a brave knight", "params": {}, "outline": {}, "draft": "",
        "critic_score": 0.0, "critic_feedback": "", "retry_count": 0,
        "final_story": "", "metadata": {},
    })
    assert len(result["final_story"]) > 0
    assert "edit" in result["metadata"]["pipeline"]["stages_completed"]


def test_pipeline_max_retries(monkeypatch):
    # LLM always produces a short draft → critic always fails → editor still runs
    monkeypatch.setattr("pipeline.nodes.get_chat_llm", lambda **kw: _mock_llm("short draft"))
    monkeypatch.setattr("pipeline.rubric.get_chat_llm", lambda **kw: _mock_llm("NO"))
    from pipeline.graph import build_pipeline
    p = build_pipeline()
    result = p.invoke({
        "request": "test", "params": {}, "outline": {}, "draft": "",
        "critic_score": 0.0, "critic_feedback": "", "retry_count": 0,
        "final_story": "", "metadata": {},
    })
    assert result["retry_count"] <= 2
    assert len(result["final_story"]) > 0  # editor always produces output
