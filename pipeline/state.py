from typing import TypedDict


class StoryState(TypedDict):
    request: str           # original user prompt
    params: dict           # title/genre/audience/moral overrides from tool args
    outline: dict          # planner output
    draft: str             # writer output (current best draft)
    critic_score: float    # 0.0–1.0
    critic_feedback: str   # passed back to writer on retry
    retry_count: int       # incremented each time writer runs after first pass
    final_story: str       # editor output (complete file text including header)
    metadata: dict         # v2 schema record built progressively through pipeline
