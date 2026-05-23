from langgraph.graph import StateGraph, END
from pipeline.state import StoryState
from pipeline.nodes import planner, writer, critic, editor

MAX_RETRIES = 2


def _critic_gate(state: StoryState) -> str:
    if state["critic_score"] >= 0.75:
        return "editor"
    if state.get("retry_count", 0) >= MAX_RETRIES:
        return "editor"  # best draft so far goes to editor
    return "writer"


def build_pipeline() -> StateGraph:
    g = StateGraph(StoryState)
    g.add_node("planner", planner)
    g.add_node("writer", writer)
    g.add_node("critic", critic)
    g.add_node("editor", editor)
    g.set_entry_point("planner")
    g.add_edge("planner", "writer")
    g.add_edge("writer", "critic")
    g.add_conditional_edges("critic", _critic_gate, {"writer": "writer", "editor": "editor"})
    g.add_edge("editor", END)
    return g.compile()


pipeline = build_pipeline()
