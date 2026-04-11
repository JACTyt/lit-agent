from langchain.tools import tool
from rag.retriever import get_retriever
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from rag.ingest import ensure_books_ingested
from dotenv import load_dotenv
import json
import os
import re
from pathlib import Path

load_dotenv()
DB_PATH = "rag/chroma_db"
LIBRARY_DIR = Path("library")

# Create embeddings function
embeddings = OpenAIEmbeddings()


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
    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    return _model_response_to_text(llm(prompt))


def _get_vector_store() -> Chroma:
    # Keep retrieval index in sync with local books/library before each retrieval action.
    try:
        ensure_books_ingested(verbose=False)
    except Exception:
        # Fall back to existing persisted DB if re-ingestion cannot run right now.
        pass
    return Chroma(
        persist_directory=DB_PATH,
        embedding_function=embeddings
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
    """Locate a book text file in the active library locations."""
    candidates = []
    normalized = book_name.strip()
    if not normalized:
        return None

    if normalized.lower().endswith(".txt"):
        candidates.append(normalized)
    else:
        candidates.append(f"{normalized}.txt")

    for base_dir in ("library", "books"):
        for candidate in candidates:
            path = os.path.join(base_dir, candidate)
            if os.path.isfile(path):
                return path
    return None


def _persist_classification_metadata(book_name: str, metadata: dict) -> str | None:
    """Persist book classification metadata as a JSON sidecar next to the book."""
    source_path = _find_book_file(book_name)
    if not source_path:
        return None
    if not _is_within_library(Path(source_path)):
        return None

    sidecar_path = os.path.splitext(source_path)[0] + ".metadata.json"
    payload = {
        "book_name": os.path.splitext(os.path.basename(source_path))[0],
        "source_path": source_path,
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
        "Write Part 1 of an original story in 2 paragraphs using this outline. "
        "Focus on the setup, the detectives or protagonists, the initial mystery or conflict, and the first major challenge. "
        "Do not resolve the story yet.\n\n"
        f"Outline JSON:\n{json.dumps(outline or final_record, ensure_ascii=False, indent=2)}"
    )
    part_two_prompt = (
        "Write Part 2 of the same story in 2 paragraphs. "
        "Continue directly from Part 1, escalate the conflict, solve the mystery, and land the moral naturally through the ending. "
        "Do not repeat Part 1.\n\n"
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

    if not part_one:
        part_one = (
            f"{final_record['title']} opened with two detectives working a case that looked simple at first. "
            f"They followed clues through a city of locked doors, false leads, and strained trust."
        )

    if not part_two:
        part_two = (
            f"As the pressure grew, the detectives had to trust each other's instincts to uncover the truth. "
            f"By combining their skills and staying honest with one another, they uncovered the murderer and learned that {final_record['moral'].lower()}"
        )

    story_body = f"{part_one.rstrip()}\n\n{part_two.lstrip()}"

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
        try:
            docs = retriever.get_relevant_documents(query)
        except Exception:
            docs = retriever._get_relevant_documents(query, run_manager=None)
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
        llm = ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4o-mini"), temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
        response = llm(prompt)
        if book_name:
            try:
                parsed = json.loads(str(response))
                if isinstance(parsed, dict):
                    record = {**fallback_record, **parsed}
                    _persist_classification_metadata(book_name, record)
            except Exception:
                _persist_classification_metadata(book_name, fallback_record)
        return response
    except Exception:
        structured = fallback_record
        if book_name:
            try:
                _persist_classification_metadata(book_name, structured)
            except Exception:
                pass
        return json.dumps(structured, ensure_ascii=False, indent=2)
"""
@tool("MultiBookSearch", description="Searches all ingested books")
def search_books(query: str, book_name: str = None) -> str:
    retriever = get_retriever(book_name)
    
    # required in new LangChain
    docs = retriever._get_relevant_documents(query, run_manager=None)
    
    print("Retrieved docs:", len(docs))
    
    if not docs:
        return "No relevant documents found."

    results = []
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("book_name", "Unknown Source")
        results.append(f"Result {i} — Book: {source}\n{doc.page_content}")
    return "\n\n".join(results)
"""

    
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
        try:
            docs = retriever.get_relevant_documents(query_or_text)  # preferred API
        except Exception:
            docs = retriever._get_relevant_documents(query_or_text, run_manager=None)
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
        llm = ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4o-mini"), temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
        # ChatOpenAI usually supports calling with a single string prompt
        summary = llm(prompt)
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
        try:
            docs = retriever.get_relevant_documents(query)
        except Exception:
            docs = retriever._get_relevant_documents(query, run_manager=None)
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
        llm = ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4o-mini"), temperature=0.2, api_key=os.getenv("OPENAI_API_KEY"))
        moral = llm(prompt)
        return moral
    except Exception:
        # Heuristic fallback: pick sentences with keywords or return first sentence of combined content
        import re

        sentences = re.split(r"(?<=[.!?]) +", combined.strip())
        for s in sentences:
            if any(k in s.lower() for k in ("moral", "lesson", "learn", "should")):
                return s.strip()
        return (sentences[0].strip() if sentences else "No moral found from the provided text.")


toolbox = [create_book, read_book, update_book_metadata, rename_book, classify_book, retrieve_context, summarize, moral_creator]