from langchain.tools import tool
from langchain_chroma import Chroma
from dotenv import load_dotenv
import json
import os
import re
from pathlib import Path

from agent.llm_provider import get_chat_llm, get_embeddings
from rag.constants import DB_PATH, COLLECTION_NAME
from rag.ingest import ensure_books_ingested
from rag.retriever import get_retriever

load_dotenv()
LIBRARY_DIR = Path("library")

# Create embeddings function (shared singleton — see llm_provider.get_embeddings)
embeddings = get_embeddings()

_llm_cache: dict = {}


def _get_cached_llm(temperature: float):
    if temperature not in _llm_cache:
        _llm_cache[temperature] = get_chat_llm(temperature=temperature)
    return _llm_cache[temperature]


def _library_root() -> Path:
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    return LIBRARY_DIR.resolve()


def _sanitize_book_stem(value: str) -> str:
    cleaned = re.sub(r"[^\w\s.-]", "", value.strip(), flags=re.UNICODE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().replace(" ", "_")
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    return cleaned or "untitled_book"


def _normalize_label(value: str) -> str:
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).lower()


def _validate_library_leaf_name(book_name: str) -> str:
    raw = (book_name or "").strip()
    if not raw:
        raise ValueError("Book name cannot be empty.")

    candidate = Path(raw)
    if candidate.is_absolute() or len(candidate.parts) != 1:
        raise ValueError("Book operations are restricted to filenames in library/ only.")

    stem = candidate.stem
    if stem in {"", ".", ".."} or any(part in {".", ".."} for part in candidate.parts):
        raise ValueError("Book operations are restricted to filenames in library/ only.")
    return stem


def _unique_library_text_path(stem: str) -> Path:
    root = _library_root()
    safe_stem = _sanitize_book_stem(stem)
    candidate = root / f"{safe_stem}.txt"
    counter = 2
    while candidate.exists():
        candidate = root / f"{safe_stem}_{counter}.txt"
        counter += 1
    return candidate


def _resolve_library_text_path(book_name: str, must_exist: bool = True) -> Path:
    stem = _validate_library_leaf_name(book_name)
    root = _library_root()
    exact_name = Path(book_name).name
    if exact_name.lower().endswith(".txt"):
        exact_candidate = root / exact_name
    else:
        exact_candidate = root / f"{stem}.txt"

    if exact_candidate.exists():
        return exact_candidate

    normalized = _normalize_label(stem)
    matches = [path for path in root.glob("*.txt") if _normalize_label(path.stem) == normalized]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Multiple books match '{book_name}'. Use a more exact filename.")

    safe_candidate = root / f"{_sanitize_book_stem(stem)}.txt"
    if must_exist:
        raise FileNotFoundError(f"Book not found in library/: {book_name}")
    return safe_candidate


def _book_sidecar_path(book_path: Path) -> Path:
    return book_path.with_suffix(".metadata.json")


def _is_within_library(path: Path) -> bool:
    try:
        path.resolve().relative_to(_library_root())
        return True
    except Exception:
        return False


def _load_book_metadata(book_path: Path) -> dict:
    sidecar_path = _book_sidecar_path(book_path)
    if not sidecar_path.exists():
        return {}
    try:
        with open(sidecar_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_book_metadata(book_path: Path, payload: dict) -> Path:
    sidecar_path = _book_sidecar_path(book_path)
    with open(sidecar_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return sidecar_path


def _model_response_to_text(response) -> str:
    return getattr(response, "content", None) or str(response)


def _extract_json_object(text: str) -> dict:
    """Best-effort JSON extraction from model output.

    Accepts either a raw JSON string or a response that embeds a JSON object
    inside extra text / code fences.
    """
    if not text:
        return {}

    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        try:
            parsed = json.loads(fenced_match.group(1))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            pass

    object_match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if object_match:
        candidate = object_match.group(0)
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    return {}


def _call_llm(prompt: str, temperature: float = 0.7) -> str:
    llm = _get_cached_llm(temperature)
    return _model_response_to_text(llm(prompt))


def _strip_generated_headers(text: str) -> str:
    """Remove accidental header blocks from generated story text.

    Some model outputs may include their own Title/Genre/Moral lines. We keep a
    single canonical header written by CreateBook and store only narrative text
    in the Story section.
    """
    if not text:
        return ""

    lines = text.splitlines()
    filtered = []
    skipping_prefix = True
    header_keys = (
        "title:",
        "genre:",
        "theme:",
        "audience:",
        "reading level:",
        "moral:",
        "story:",
    )

    for line in lines:
        stripped = line.strip().lower()
        if skipping_prefix and (not stripped or stripped.startswith(header_keys)):
            continue
        skipping_prefix = False
        filtered.append(line)

    return "\n".join(filtered).strip()


def _story_word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def _is_low_quality_story(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return True

    generic_markers = (
        "began with its main characters facing an unexpected challenge",
        "as the story reached its turning point",
        "navigated through setbacks",
    )

    if any(marker in lowered for marker in generic_markers):
        return True

    # Enforce a minimum narrative depth for a "book" creation request.
    return _story_word_count(lowered) < 450


def _extract_character_triplet(outline: dict, title: str) -> tuple[str, str, str]:
    protagonist = "Mira"
    helper = "Pip"
    rival = "Brindle"

    raw = outline.get("characters") if isinstance(outline, dict) else None
    names = []

    if isinstance(raw, dict):
        for key in ("protagonist", "main", "hero", "helper", "friend", "mentor", "rival", "antagonist"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                names.append(value.strip())
            elif isinstance(value, dict):
                nested = value.get("name")
                if isinstance(nested, str) and nested.strip():
                    names.append(nested.strip())
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item.strip():
                names.append(item.strip())
            elif isinstance(item, dict):
                nested = item.get("name")
                if isinstance(nested, str) and nested.strip():
                    names.append(nested.strip())

    if names:
        protagonist = names[0]
    if len(names) > 1:
        helper = names[1]
    if len(names) > 2:
        rival = names[2]

    if protagonist.lower() == helper.lower():
        helper = f"{protagonist}'s Friend"
    if rival.lower() in {protagonist.lower(), helper.lower()}:
        rival = f"The Shadow of {title.split()[0]}"

    return protagonist, helper, rival


def _build_structured_fallback_story(final_record: dict, outline: dict, request: str) -> str:
    title = final_record.get("title", "Untitled Story")
    theme = final_record.get("theme", "growth and courage")
    moral = final_record.get("moral", "Small choices build a better future.")
    audience = (final_record.get("audience") or "general").lower()

    setting = "the river town of Lantern Vale"
    conflict = "a mystery that threatens the town's yearly festival"
    resolution = "truth, teamwork, and patience restore balance"

    if isinstance(outline, dict):
        if isinstance(outline.get("setting"), str) and outline.get("setting").strip():
            setting = outline.get("setting").strip()
        if isinstance(outline.get("conflict"), str) and outline.get("conflict").strip():
            conflict = outline.get("conflict").strip()
        if isinstance(outline.get("resolution"), str) and outline.get("resolution").strip():
            resolution = outline.get("resolution").strip()

    protagonist, helper, rival = _extract_character_triplet(outline or {}, title)
    tone_line = "The language stayed warm and clear so young readers could follow each turn."
    if "children" not in audience:
        tone_line = "The language balanced vivid imagery with reflective moments."

    paragraphs = [
        (
            f"On the edge of {setting}, {protagonist} carried a satchel full of stubby pencils and folded paper. "
            f"While other children hurried past the old market square, {protagonist} stopped to sketch faces, rooftops, and stray cats curled in sunlight. "
            f"Everyone knew {protagonist} could notice beauty in ordinary things, but almost no one knew how deeply {protagonist} feared making mistakes in front of others. "
            f"That fear mattered now, because the whole town was preparing for a celebration and trouble had already begun to spread."
        ),
        (
            f"The first sign of danger arrived at dawn: bright festival banners had been painted overnight, then somehow faded before breakfast into pale ghosts of color. "
            f"Vendors blamed the weather, neighbors blamed one another, and the mayor announced that if the fading continued, the celebration would be canceled. "
            f"When {helper} found {protagonist} staring at a blank page near the fountain, {helper} whispered that this might be more than bad paint. "
            f"It might be connected to {conflict}, and only someone patient enough to observe every detail could solve it."
        ),
        (
            f"By afternoon, {protagonist} and {helper} followed faint trails of color dust through alleys, under bridges, and behind the old clocktower. "
            f"There they discovered footprints and a locked wooden chest etched with symbols that matched patterns in {protagonist}'s sketchbook. "
            f"Before they could inspect it further, {rival} stepped from the shadows, certain that {protagonist} had no right to meddle in serious matters. "
            f"The accusation stung, and for a moment {protagonist} almost stepped back into silence."
        ),
        (
            f"Instead of arguing, {protagonist} opened the sketchbook and showed a sequence of drawings made over several days: faded murals, spilled pigments, and the same symbol near each site. "
            f"The drawings revealed a pattern no one else had seen. "
            f"Even {rival} paused, surprised that careful observation could uncover what loud guesses had missed. "
            f"Together they carried the chest to the library, where an elderly archivist explained that the symbols marked old recipes for unstable dyes, beautiful at first but doomed to vanish unless mixed with patience and precision."
        ),
        (
            f"Now the challenge changed from mystery to action. "
            f"The town had one evening left to repaint every banner and sign, and panic made everyone clumsy. "
            f"{protagonist} organized teams: one to grind pigments, one to prepare cloth, one to test each mixture under lamplight, and one to repaint in gentle layers. "
            f"{helper} kept spirits high with songs, while {rival} climbed ladders and took the hardest corners no one else could reach."
        ),
        (
            f"As the moon rose, mistakes still happened. Lines wobbled, colors bled, and tired hands trembled. "
            f"Each time, {protagonist} resisted the urge to hide. "
            f"Instead, {protagonist} showed how to pause, breathe, and try again with steadier hands. "
            f"That quiet courage changed the mood of the square: fear became focus, and focus became shared pride."
        ),
        (
            f"At sunrise, the banners gleamed brighter than before. The celebration went ahead, and the crowd cheered not only for the colors but for the teamwork behind them. "
            f"When the mayor thanked everyone, {protagonist} finally spoke in public, crediting {helper}, {rival}, and every volunteer who stayed up through the night. "
            f"The final mural in the square captured the lesson in a single image: many different hands painting one horizon together. "
            f"{resolution.capitalize()}, and the town remembered that {moral.rstrip('.')}.")
        ,
        (
            f"Long after the festival, children visited the square to copy the mural into their own notebooks. "
            f"{protagonist} greeted each of them with spare pencils and a reminder that strong stories and strong communities begin the same way: with attention, honesty, and willingness to learn. "
            f"Whenever someone said, 'I am not talented enough,' {protagonist} smiled and pointed to the oldest, most imperfect sketch pinned above the desk. "
            f"{tone_line}"
        ),
    ]

    return "\n\n".join(p.strip() for p in paragraphs if p.strip())


def _get_vector_store() -> Chroma:
    # Keep retrieval index in sync with local books/library before each retrieval action.
    try:
        ensure_books_ingested(verbose=False)
    except Exception:
        # Fall back to existing persisted DB if re-ingestion cannot run right now.
        pass
    return Chroma(
        persist_directory=DB_PATH,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )


def _extract_taxonomy_from_text(text: str) -> dict:
    """Fallback classifier used when the LLM is unavailable.

    The categories are intentionally stable so the same book tends to map to the
    same metadata across runs.
    """
    lowered = text.lower()

    if any(word in lowered for word in ("friend", "friendship", "help", "kind", "share", "team")):
        genre = "fable"
        theme = "friendship and kindness"
    elif any(word in lowered for word in ("animal", "fox", "lion", "rabbit", "bird", "grasshopper", "ant")):
        genre = "fable"
        theme = "nature and character lessons"
    else:
        genre = "short story"
        theme = "personal growth"

    if any(word in lowered for word in ("children", "kid", "young", "school")):
        audience = "children"
    elif any(word in lowered for word in ("teen", "adolescent", "youth")):
        audience = "young adult"
    else:
        audience = "general"

    if len(text.split()) < 400:
        reading_level = "easy"
    elif len(text.split()) < 1200:
        reading_level = "middle"
    else:
        reading_level = "advanced"

    if any(word in lowered for word in ("moral", "lesson", "learn", "should")):
        lesson = "The story emphasizes a clear moral lesson."
    else:
        lesson = "The story emphasizes character growth and reflective meaning."

    return {
        "genre": genre,
        "theme": theme,
        "audience": audience,
        "reading_level": reading_level,
        "lesson_hint": lesson,
    }


def _find_book_file(book_name: str) -> str | None:
    """Locate a book text file in library/."""
    try:
        return str(_resolve_library_text_path(book_name, must_exist=True))
    except (FileNotFoundError, ValueError):
        return None


def _persist_classification_metadata(book_name: str, metadata: dict) -> str | None:
    """Persist book classification metadata as a JSON sidecar next to the book."""
    try:
        book_path = _resolve_library_text_path(book_name, must_exist=True)
    except (FileNotFoundError, ValueError):
        return None

    sidecar_path = os.path.splitext(str(book_path))[0] + ".metadata.json"
    payload = {
        "book_name": book_path.stem,
        "source_path": str(book_path),
        "classification": metadata,
    }
    with open(sidecar_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return sidecar_path


@tool(
    "CreateBook",
    response_format="content",
    description="Create an original book, save it safely into library/, and return its saved path plus metadata. Use `request` to describe the story to generate."
)
def create_book(request: str, title: str = None, genre: str = None, theme: str = None, audience: str = None, reading_level: str = None, moral: str = None) -> str:
    """Create a new original book and persist it inside library/ only."""
    outline_prompt = (
        "Create a compact story outline in valid JSON only with keys: title, genre, theme, audience, reading_level, moral, characters, conflict, resolution, setting. "
        "The outline should be specific enough to support a complete original story in multiple parts. "
        "Do not write the full story yet.\n"
        f"Requested story idea: {request}\n"
        f"Requested title: {title or 'auto'}\n"
        f"Requested genre: {genre or 'auto'}\n"
        f"Requested theme: {theme or 'auto'}\n"
        f"Requested audience: {audience or 'auto'}\n"
        f"Requested reading level: {reading_level or 'auto'}\n"
        f"Requested moral: {moral or 'auto'}\n"
    )

    try:
        outline_text = _call_llm(outline_prompt, temperature=0.4)
    except Exception:
        outline_text = ""

    outline = _extract_json_object(outline_text)
    title_value = (outline.get("title") or title or "").strip() or _sanitize_book_stem(request[:60] or "Untitled Book").replace("_", " ").title()
    fallback = _extract_taxonomy_from_text(f"{request}\n{outline_text}")

    final_record = {
        "title": title_value,
        "genre": outline.get("genre") or genre or fallback["genre"],
        "theme": outline.get("theme") or theme or fallback["theme"],
        "audience": outline.get("audience") or audience or fallback["audience"],
        "reading_level": outline.get("reading_level") or reading_level or fallback["reading_level"],
        "moral": outline.get("moral") or moral or fallback["lesson_hint"],
    }

    part_one_prompt = (
        "Write Part 1 of an original children's story in 4 rich paragraphs and at least 280 words. "
        "Include character introductions, vivid setting details, clear motivations, and an early conflict. "
        "Use concrete scenes and dialogue. Do not resolve the central conflict yet.\n\n"
        f"Story request: {request}\n"
        f"Outline JSON:\n{json.dumps(outline or final_record, ensure_ascii=False, indent=2)}"
    )
    part_two_prompt = (
        "Write Part 2 of the same story in 4 rich paragraphs and at least 280 words. "
        "Continue seamlessly from Part 1, raise stakes, deliver an emotional turning point, and resolve the conflict with a satisfying ending. "
        "Integrate the moral naturally through character choices, not as a lecture.\n\n"
        f"Story request: {request}\n"
        f"Outline JSON:\n{json.dumps(outline or final_record, ensure_ascii=False, indent=2)}"
    )

    try:
        part_one = _call_llm(part_one_prompt, temperature=0.8).strip()
    except Exception:
        part_one = ""

    try:
        part_two = _call_llm(part_two_prompt, temperature=0.8).strip()
    except Exception:
        part_two = ""

    part_one = _strip_generated_headers(part_one)
    part_two = _strip_generated_headers(part_two)

    if not part_one:
        part_one = _build_structured_fallback_story(final_record, outline, request)

    if not part_two:
        part_two = ""

    story_body = _strip_generated_headers(f"{part_one.rstrip()}\n\n{part_two.lstrip()}")

    if _is_low_quality_story(story_body):
        single_pass_prompt = (
            "Write a complete, captivating children's story between 700 and 1100 words. "
            "The story must include: a memorable protagonist, at least two supporting characters, a specific setting, a concrete conflict, rising action, a turning point, and a heartfelt resolution. "
            "Use descriptive language, short dialogue snippets, and emotionally meaningful choices. "
            "Do not output headers, bullets, or JSON; output only narrative prose.\n\n"
            f"Story request: {request}\n"
            f"Story profile: {json.dumps(outline or final_record, ensure_ascii=False)}"
        )
        try:
            enhanced = _strip_generated_headers(_call_llm(single_pass_prompt, temperature=0.85).strip())
        except Exception:
            enhanced = ""

        if not _is_low_quality_story(enhanced):
            story_body = enhanced
        else:
            story_body = _build_structured_fallback_story(final_record, outline, request)

    book_path = _unique_library_text_path(final_record["title"])
    book_text = (
        f"Title: {final_record['title']}\n"
        f"Genre: {final_record['genre']}\n"
        f"Theme: {final_record['theme']}\n"
        f"Audience: {final_record['audience']}\n"
        f"Reading level: {final_record['reading_level']}\n"
        f"Moral: {final_record['moral']}\n\n"
        f"Story:\n{story_body.strip()}\n"
    )
    book_path.write_text(book_text, encoding="utf-8")

    sidecar_payload = {
        "book_name": book_path.stem,
        "source_path": str(book_path),
        "creation_request": request,
        "classification": final_record,
        "story_preview": story_body[:600],
    }
    sidecar_path = _save_book_metadata(book_path, sidecar_payload)

    try:
        ensure_books_ingested(verbose=False)
    except Exception:
        pass

    return json.dumps(
        {
            "status": "created",
            "path": str(book_path),
            "metadata_path": str(sidecar_path),
            "classification": final_record,
            "story": story_body,
        },
        ensure_ascii=False,
        indent=2,
    )


@tool(
    "ReadBook",
    response_format="content",
    description="Read a book safely from library/ and return its text plus any saved metadata."
)
def read_book(book_name: str) -> str:
    """Read a book stored in library/ without allowing path traversal."""
    book_path = _resolve_library_text_path(book_name)
    content = book_path.read_text(encoding="utf-8")
    metadata = _load_book_metadata(book_path)
    return (
        f"Path: {book_path}\n"
        f"Metadata: {json.dumps(metadata, ensure_ascii=False, indent=2)}\n\n"
        f"{content}"
    )


@tool(
    "UpdateBookMetadata",
    response_format="content",
    description="Update the metadata sidecar for a book in library/ safely. This updates category information without leaving the library folder."
)
def update_book_metadata(book_name: str, genre: str = None, theme: str = None, audience: str = None, reading_level: str = None, moral: str = None) -> str:
    """Update metadata for a book inside library/ only."""
    book_path = _resolve_library_text_path(book_name)
    metadata = _load_book_metadata(book_path)
    classification = dict(metadata.get("classification", {}))

    updates = {
        "genre": genre,
        "theme": theme,
        "audience": audience,
        "reading_level": reading_level,
        "moral": moral,
    }
    for key, value in updates.items():
        if value:
            classification[key] = value

    metadata["book_name"] = book_path.stem
    metadata["source_path"] = str(book_path)
    metadata["classification"] = classification
    sidecar_path = _save_book_metadata(book_path, metadata)

    return json.dumps(
        {
            "status": "updated",
            "path": str(book_path),
            "metadata_path": str(sidecar_path),
            "classification": classification,
        },
        ensure_ascii=False,
        indent=2,
    )


@tool(
    "RenameBook",
    response_format="content",
    description="Rename or move a book safely within library/ by changing its filename and matching metadata sidecar."
)
def rename_book(book_name: str, new_name: str) -> str:
    """Rename a book inside library/ only."""
    source_path = _resolve_library_text_path(book_name)
    new_stem = _sanitize_book_stem(_validate_library_leaf_name(new_name))
    root = _library_root()
    target_path = root / f"{new_stem}.txt"

    if source_path.resolve() == target_path.resolve():
        return json.dumps(
            {
                "status": "unchanged",
                "path": str(source_path),
            },
            ensure_ascii=False,
            indent=2,
        )

    if target_path.exists():
        target_path = _unique_library_text_path(new_stem)

    source_sidecar = _book_sidecar_path(source_path)
    target_sidecar = _book_sidecar_path(target_path)

    source_path.rename(target_path)
    if source_sidecar.exists():
        source_sidecar.rename(target_sidecar)
        metadata = _load_book_metadata(target_path)
        metadata["book_name"] = target_path.stem
        metadata["source_path"] = str(target_path)
        classification = dict(metadata.get("classification", {}))
        classification["title"] = target_path.stem.replace("_", " ")
        metadata["classification"] = classification
        _save_book_metadata(target_path, metadata)
    elif target_sidecar.exists():
        metadata = _load_book_metadata(target_path)
        metadata["book_name"] = target_path.stem
        metadata["source_path"] = str(target_path)
        _save_book_metadata(target_path, metadata)

    try:
        ensure_books_ingested(verbose=False)
    except Exception:
        pass

    return json.dumps(
        {
            "status": "renamed",
            "from": str(source_path),
            "to": str(target_path),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool(
    "ClassifyBook",
    response_format="content",
    description="Classify a book using librarian-style metadata: genre, theme, audience, reading level, and a short rationale. Provide `book_name` to classify a specific book in the library."
)
def classify_book(query: str, book_name: str = None) -> str:
    """Return structured metadata for a book or query.

    This tool is meant to produce consistent catalog-style metadata.
    """
    if book_name:
        retriever = get_retriever(book_name)
        docs = retriever.invoke(query)
    else:
        vector_store = _get_vector_store()
        docs = vector_store.similarity_search(query, k=4)

    combined = "\n\n".join(d.page_content for d in docs)
    fallback = _extract_taxonomy_from_text(combined or query)
    fallback_record = {
        "title": book_name or "Unknown title",
        "genre": fallback["genre"],
        "theme": fallback["theme"],
        "audience": fallback["audience"],
        "reading_level": fallback["reading_level"],
        "rationale": fallback["lesson_hint"],
        "confidence": "heuristic",
    }

    prompt = (
        "Classify the following book using stable librarian metadata. "
        "Return JSON with keys: title, genre, theme, audience, reading_level, rationale, confidence. "
        "Keep the category choices consistent and avoid inventing facts not supported by the text.\n\n"
        + combined
    )

    try:
        response = _call_llm(prompt, temperature=0)
        if book_name:
            parsed = _extract_json_object(response)
            record = {**fallback_record, **parsed} if parsed else fallback_record
            _persist_classification_metadata(book_name, record)
        return response
    except Exception:
        structured = fallback_record
        if book_name:
            try:
                _persist_classification_metadata(book_name, structured)
            except Exception:
                pass
        return json.dumps(structured, ensure_ascii=False, indent=2)


@tool("GetContext", response_format="content_and_artifact", description="Retrieve grounded passages from the library to support librarian tasks such as classification, summary, and moral extraction.")
def retrieve_context(query: str):
    """Retrieve information to help answer a query.

    Use this when you need direct evidence from a book before classifying,
    summarizing, organizing, or explaining its moral.
    """
    vector_store = _get_vector_store()
    retrieved_docs = vector_store.similarity_search(query, k=2)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs


@tool("Summarize", response_format="content", description="Summarize book passages in a concise librarian style. If `book_name` is provided, restrict search to that book and preserve consistent terminology.")
def summarize(query_or_text: str, book_name: str = None) -> str:
    """Return a concise summary for a query or provided text.

    Behavior:
    - If `book_name` is provided, uses retriever for that book.
    - If the input looks like a short query, performs a similarity search and summarizes the retrieved passages.
    - Produces a factual, source-grounded summary suitable for cataloging or librarian review.
    - Attempts to call the local ChatOpenAI model; on failure returns the raw concatenated context plus a suggested prompt.
    """
    # Determine whether caller passed raw text or a short query
    is_long_text = len(query_or_text.split()) > 80

    if book_name:
        retriever = get_retriever(book_name)
        docs = retriever.invoke(query_or_text)
    else:
        if is_long_text:
            # Treat as raw text to summarize
            docs = [type("D", (), {"metadata": {"source": "input"}, "page_content": query_or_text})]
        else:
            vector_store = _get_vector_store()
            docs = vector_store.similarity_search(query_or_text, k=4)

    serialized = "\n\n".join(f"Source: {getattr(d, 'metadata', {})}\nContent: {getattr(d, 'page_content', '')}" for d in docs)

    prompt = (
        "Summarize the following passages concisely (2-4 sentences) in a librarian style. "
        "Focus on the main plot, theme, or purpose, and keep terminology consistent with the source text. "
        "For each main point include a short citation indicating the source metadata.\n\n"
        + serialized
    )

    # Try to call the LLM; if it fails, return the context and a suggested prompt
    try:
        summary = _call_llm(prompt, temperature=0)
        return summary
    except Exception as e:
        fallback = (
            f"LLM call failed: {e}\n\n--- Raw context below ---\n\n{serialized}\n\nSuggested prompt to feed to an LLM:\n{prompt}"
        )
        return fallback


@tool("MoralCreator", response_format="content", description="Extract or infer the moral, lesson, or takeaway from a book in a consistent librarian style. Provide `book_name` to focus on a single book.")
def moral_creator(query: str, book_name: str = None) -> str:
    """Generate a short moral or lesson based on retrieved passages.

    This tool prefers to use the LLM; if unavailable it returns a heuristic-based one-liner.
    Use it to explain the central lesson of a story in a concise and repeatable way.
    """
    # Retrieve context
    if book_name:
        retriever = get_retriever(book_name)
        docs = retriever.invoke(query)
    else:
        vector_store = _get_vector_store()
        docs = vector_store.similarity_search(query, k=4)

    combined = "\n\n".join(d.page_content for d in docs)
    prompt = (
        "Based on the passages below, write a single-sentence moral or lesson that captures the main takeaway. "
        "Keep it general, applicable, and aligned with the book's evidence. Use librarian-style wording that stays consistent across similar requests.\n\n"
        + combined
    )

    try:
        moral = _call_llm(prompt, temperature=0.2)
        return moral
    except Exception:
        # Heuristic fallback: pick sentences with keywords or return first sentence of combined content
        import re

        sentences = re.split(r"(?<=[.!?]) +", combined.strip())
        for s in sentences:
            if any(k in s.lower() for k in ("moral", "lesson", "learn", "should")):
                return s.strip()
        return (sentences[0].strip() if sentences else "No moral found from the provided text.")


@tool(
    "EditBook",
    response_format="content",
    description=(
        "Edit the narrative content of an existing book in library/. "
        "Provide `instruction` describing what to change (e.g. 'make the ending happier', "
        "'add a rival character in chapter 2', 'rewrite the opening paragraph'). "
        "Optionally supply `section_hint` to narrow the edit to a specific scene or passage. "
        "Saves the revised text back to the same file."
    ),
)
def edit_book(book_name: str, instruction: str, section_hint: str = None) -> str:
    """Edit the narrative text of an existing book inside library/ only."""
    book_path = _resolve_library_text_path(book_name)
    content = book_path.read_text(encoding="utf-8")

    header_lines: list[str] = []
    story_lines: list[str] = []
    in_story = False
    for line in content.splitlines():
        if not in_story and line.strip().lower().startswith("story:"):
            in_story = True
            after_label = line[line.lower().find("story:") + 6:]
            if after_label.strip():
                story_lines.append(after_label)
        elif in_story:
            story_lines.append(line)
        else:
            header_lines.append(line)

    story_body = "\n".join(story_lines).strip()
    header = "\n".join(header_lines).strip()

    if section_hint:
        prompt = (
            f"You are editing a story. Locate the section that relates to: '{section_hint}'.\n"
            f"Apply this change: {instruction}\n"
            f"Return the COMPLETE revised story (all parts), not only the changed section.\n"
            f"Output only narrative prose — no titles, headers, or metadata.\n\n"
            f"Original story:\n{story_body}"
        )
    else:
        prompt = (
            f"Revise the following story according to this instruction: {instruction}\n"
            f"Return the complete revised story narrative.\n"
            f"Output only narrative prose — no titles, headers, or metadata.\n\n"
            f"Original story:\n{story_body}"
        )

    try:
        revised_body = _call_llm(prompt, temperature=0.75).strip()
        revised_body = _strip_generated_headers(revised_body)
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2)

    new_content = f"{header}\n\nStory:\n{revised_body}\n"
    book_path.write_text(new_content, encoding="utf-8")

    metadata = _load_book_metadata(book_path)
    metadata["last_edit_instruction"] = instruction
    _save_book_metadata(book_path, metadata)

    try:
        ensure_books_ingested(verbose=False)
    except Exception:
        pass

    return json.dumps(
        {
            "status": "edited",
            "path": str(book_path),
            "instruction": instruction,
            "story_preview": revised_body[:400],
        },
        ensure_ascii=False,
        indent=2,
    )


@tool(
    "AnalyzeStory",
    response_format="content",
    description=(
        "Perform deep literary analysis of a book from library/. "
        "Returns: motivation (what drives the protagonist), thesis (central message), "
        "thoughts (key themes), key_moments (pivotal scene explanations), "
        "brief_description (reader-friendly blurb), and emotional_arc. "
        "Optionally supply `focus` to zoom in on a particular aspect."
    ),
)
def analyze_story(book_name: str, focus: str = None) -> str:
    """Return structured literary analysis of a book inside library/."""
    book_path = _resolve_library_text_path(book_name)
    content = book_path.read_text(encoding="utf-8")
    metadata = _load_book_metadata(book_path)

    focus_line = f"\nPay particular attention to: {focus}\n" if focus else ""

    prompt = (
        "Analyze the following story and return ONLY a valid JSON object with exactly these keys:\n"
        "{\n"
        '  "motivation": "What drives the protagonist — their core desire, fear, or need",\n'
        '  "thesis": "The central argument or insight the story makes about life, people, or society",\n'
        '  "thoughts": ["key theme or idea 1", "key theme or idea 2", "key theme or idea 3"],\n'
        '  "key_moments": [\n'
        '    {"moment": "brief scene label", "explanation": "why this moment matters to the whole story"}\n'
        "  ],\n"
        '  "brief_description": "2-3 sentence reader-friendly blurb without major spoilers",\n'
        '  "emotional_arc": "How the emotional tone shifts from opening to close"\n'
        "}\n"
        "Base every answer strictly on evidence from the text. Do not invent facts.\n"
        + focus_line
        + f"\n\nStory text:\n{content}"
    )

    fallback: dict = {
        "motivation": "Analysis unavailable — LLM call failed.",
        "thesis": "Analysis unavailable — LLM call failed.",
        "thoughts": [],
        "key_moments": [],
        "brief_description": metadata.get("classification", {}).get("theme", "No description available."),
        "emotional_arc": "Analysis unavailable — LLM call failed.",
    }

    try:
        raw = _call_llm(prompt, temperature=0.3)
        parsed = _extract_json_object(raw)
        result = {**fallback, **parsed} if parsed else {"raw_analysis": raw, **fallback}
    except Exception as exc:
        result = {**fallback, "error": str(exc)}

    try:
        meta = _load_book_metadata(book_path)
        meta["analysis"] = result
        _save_book_metadata(book_path, meta)
    except Exception:
        pass

    return json.dumps(result, ensure_ascii=False, indent=2)


toolbox = [
    create_book,
    read_book,
    edit_book,
    update_book_metadata,
    rename_book,
    classify_book,
    retrieve_context,
    summarize,
    moral_creator,
    analyze_story,
]