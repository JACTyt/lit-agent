from langchain.tools import tool
from rag.retriever import get_retriever
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from rag.ingest import ensure_books_ingested
from dotenv import load_dotenv
import json
import os

load_dotenv()
DB_PATH = "rag/chroma_db"

# Create embeddings function
embeddings = OpenAIEmbeddings()


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


toolbox = [classify_book, retrieve_context, summarize, moral_creator]