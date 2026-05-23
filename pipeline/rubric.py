import re
from agent.llm_provider import get_chat_llm


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def _has_conflict(text: str) -> bool:
    markers = ("problem", "challenge", "danger", "trouble", "threat",
               "conflict", "struggle", "obstacle", "difficult", "enemy")
    return any(m in text.lower() for m in markers)


def _has_resolution(text: str) -> bool:
    markers = ("resolved", "learned", "discovered", "finally", "at last",
               "in the end", "succeeded", "overcame", "restored", "saved")
    return any(m in text.lower() for m in markers)


def _moral_aligned(draft: str, outline: dict) -> bool:
    moral = (outline.get("moral") or "").strip()
    if not moral:
        return True  # no moral to check — don't penalise
    try:
        llm = get_chat_llm(temperature=0)
        prompt = (
            f"Does this story clearly reflect the moral: '{moral}'?\n"
            f"Answer YES or NO only.\n\n"
            f"Story excerpt:\n{draft[:800]}"
        )
        answer = (llm.invoke(prompt).content or "").strip().upper()
        return answer.startswith("YES")
    except Exception:
        return True  # don't penalise on LLM failure


def score_draft(draft: str, outline: dict) -> tuple[float, str]:
    """Return (score 0.0–1.0, feedback string for writer retry)."""
    score = 0.0
    issues: list[str] = []
    moral = (outline.get("moral") or "").strip()

    word_count_ok = _word_count(draft) >= 600
    if word_count_ok:
        score += 0.25
    else:
        issues.append("Story is too short (under 600 words).")

    if _has_conflict(draft):
        score += 0.25
    else:
        issues.append("No clear conflict detected — add a concrete problem or danger.")

    if _has_resolution(draft):
        score += 0.25
    else:
        issues.append("No satisfying resolution detected — the story must reach a clear ending.")

    # Only check moral alignment when a moral is specified and draft is long enough
    if moral and word_count_ok:
        if _moral_aligned(draft, outline):
            score += 0.25
        else:
            issues.append(f"Story does not clearly reflect the moral: '{moral}'.")

    feedback = " ".join(issues) if issues else "Draft meets all criteria."
    return round(score, 2), feedback
