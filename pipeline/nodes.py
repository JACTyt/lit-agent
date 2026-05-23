import json
from agent.llm_provider import get_chat_llm
from agent.tools import _extract_json_object, _strip_generated_headers, _extract_taxonomy_from_text
from pipeline.state import StoryState


def planner(state: StoryState) -> StoryState:
    llm = get_chat_llm(temperature=0.4)
    prompt = (
        "Create a compact story outline in valid JSON only with keys: "
        "title, genre, theme, audience, reading_level, moral, characters, conflict, resolution, setting. "
        "Be specific enough to support a full multi-part story.\n"
        f"Request: {state['request']}\n"
        f"Overrides: {json.dumps(state.get('params', {}))}"
    )
    raw = llm.invoke(prompt).content or ""
    outline = _extract_json_object(raw)
    fallback = _extract_taxonomy_from_text(state["request"])
    params = state.get("params", {})
    title = (outline.get("title") or params.get("title") or state["request"][:60]).strip()

    metadata: dict = {
        "version": 2,
        "classification": {
            "title": title,
            "genre": outline.get("genre") or params.get("genre") or fallback["genre"],
            "theme": outline.get("theme") or params.get("theme") or fallback["theme"],
            "audience": outline.get("audience") or params.get("audience") or fallback["audience"],
            "reading_level": outline.get("reading_level") or params.get("reading_level") or fallback["reading_level"],
            "moral": outline.get("moral") or params.get("moral") or fallback["lesson_hint"],
        },
        "pipeline": {"stages_completed": ["plan"]},
        "analysis": {},
        "edit_history": [],
        "characters_path": None,
    }

    # Extract characters from outline and carry through pipeline for CreateBook to write
    raw_chars = outline.get("characters") or {}
    char_list = []
    if isinstance(raw_chars, list):
        for c in raw_chars:
            if isinstance(c, str):
                char_list.append({"name": c, "role": "character", "traits": [], "arc": "", "first_appears": ""})
            elif isinstance(c, dict):
                char_list.append({
                    "name": c.get("name", "Unknown"),
                    "role": c.get("role", "character"),
                    "traits": c.get("traits", []),
                    "arc": c.get("arc", ""),
                    "first_appears": c.get("first_appears", ""),
                })
    elif isinstance(raw_chars, dict):
        for role, info in raw_chars.items():
            name = info if isinstance(info, str) else (info.get("name", role) if isinstance(info, dict) else role)
            char_list.append({"name": name, "role": role, "traits": [], "arc": "", "first_appears": ""})

    from datetime import datetime as _dt
    char_data = {
        "version": 1,
        "story": "",  # filled in by CreateBook when path is known
        "extracted_at": _dt.utcnow().isoformat() + "Z",
        "world": {
            "setting": outline.get("setting", ""),
            "time_period": "",
            "tone": outline.get("theme", ""),
        },
        "characters": char_list,
    }
    metadata["_char_data"] = char_data

    return {**state, "outline": outline, "metadata": metadata}


def writer(state: StoryState) -> StoryState:
    llm = get_chat_llm(temperature=0.8)
    is_retry = bool((state.get("critic_feedback") or "").strip())
    retry_count = state.get("retry_count", 0) + (1 if is_retry else 0)
    retry_note = f"\n\nPrevious draft issues to fix:\n{state['critic_feedback']}" if is_retry else ""
    outline_json = json.dumps(state.get("outline") or state.get("metadata", {}).get("classification", {}), ensure_ascii=False)

    p1 = (
        "Write Part 1 of an original story in 4 rich paragraphs, at least 280 words. "
        "Include character introductions, vivid setting, clear motivations, and an early conflict. "
        "Output only narrative prose — no titles, headers, or metadata."
        f"{retry_note}\n\nOutline:\n{outline_json}"
    )
    p2 = (
        "Write Part 2 continuing seamlessly from Part 1, at least 280 words. "
        "Raise stakes, deliver a turning point, and resolve the conflict. "
        "Weave the moral through character choices, not as a lecture."
        f"\n\nOutline:\n{outline_json}"
    )
    part1 = _strip_generated_headers((llm.invoke(p1).content or "").strip())
    part2 = _strip_generated_headers((llm.invoke(p2).content or "").strip())
    draft = f"{part1}\n\n{part2}".strip()

    stages = list(state.get("metadata", {}).get("pipeline", {}).get("stages_completed", ["plan"]))
    if "write" not in stages:
        stages.append("write")
    metadata = {**state.get("metadata", {}), "pipeline": {**state.get("metadata", {}).get("pipeline", {}), "stages_completed": stages}}
    return {**state, "draft": draft, "retry_count": retry_count, "metadata": metadata}


def critic(state: StoryState) -> StoryState:
    from pipeline.rubric import score_draft
    score, feedback = score_draft(state["draft"], state.get("outline", {}))

    stages = list(state.get("metadata", {}).get("pipeline", {}).get("stages_completed", []))
    if "critique" not in stages:
        stages.append("critique")
    prior_passes = state.get("metadata", {}).get("pipeline", {}).get("critic_passes", 0)
    metadata = {
        **state.get("metadata", {}),
        "pipeline": {
            **state.get("metadata", {}).get("pipeline", {}),
            "critic_score": score,
            "critic_passes": prior_passes + (1 if score >= 0.75 else 0),
            "stages_completed": stages,
        },
    }
    return {**state, "critic_score": score, "critic_feedback": feedback, "metadata": metadata}


def editor(state: StoryState) -> StoryState:
    llm = get_chat_llm(temperature=0.3)
    classification = state.get("metadata", {}).get("classification", {})
    prompt = (
        "Polish the following story: improve flow, remove redundancy, ensure the moral emerges naturally. "
        "Return only the improved narrative prose — no titles, headers, or metadata.\n\n"
        f"Story:\n{state['draft']}"
    )
    polished = _strip_generated_headers((llm.invoke(prompt).content or state["draft"]).strip())
    header = (
        f"Title: {classification.get('title', 'Untitled')}\n"
        f"Genre: {classification.get('genre', '')}\n"
        f"Theme: {classification.get('theme', '')}\n"
        f"Audience: {classification.get('audience', '')}\n"
        f"Reading level: {classification.get('reading_level', '')}\n"
        f"Moral: {classification.get('moral', '')}\n"
    )
    final = f"{header}\nStory:\n{polished}\n"

    stages = list(state.get("metadata", {}).get("pipeline", {}).get("stages_completed", []))
    if "edit" not in stages:
        stages.append("edit")
    metadata = {**state.get("metadata", {}), "pipeline": {**state.get("metadata", {}).get("pipeline", {}), "stages_completed": stages}}
    return {**state, "final_story": final, "draft": polished, "metadata": metadata}
