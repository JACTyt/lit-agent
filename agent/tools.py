from langchain.tools import tool
from rag.retreiver import get_retriever
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = "rag/chroma_db"

# Create embeddings function
embeddings = OpenAIEmbeddings()
vector_store = Chroma(
    persist_directory=DB_PATH,
    embedding_function=embeddings
)
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

    
@tool("GetContext",response_format="content_and_artifact", description="Get context/information in book")
def retrieve_context(query: str):
    """Retrieve information to help answer a query."""
    retrieved_docs = vector_store.similarity_search(query, k=2)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs


@tool("Summarize", response_format="content", description="Summarize relevant passages for a query or text. If `book_name` is provided, restricts search to that book.")
def summarize(query_or_text: str, book_name: str = None) -> str:
    """Return a concise summary for a query or provided text.

    Behavior:
    - If `book_name` is provided, uses retriever for that book.
    - If the input looks like a short query, performs a similarity search and summarizes the retrieved passages.
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
            docs = vector_store.similarity_search(query_or_text, k=4)

    serialized = "\n\n".join(f"Source: {getattr(d, 'metadata', {})}\nContent: {getattr(d, 'page_content', '')}" for d in docs)

    prompt = (
        "Summarize the following passages concisely (2-4 sentences). For each main point include a short citation indicating the source metadata.\n\n"
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


@tool("MoralCreator", response_format="content", description="Create a short moral/lesson from a book or query. Provide `book_name` to focus on a single book.")
def moral_creator(query: str, book_name: str = None) -> str:
    """Generate a short moral or lesson based on retrieved passages.

    This tool prefers to use the LLM; if unavailable it returns a heuristic-based one-liner.
    """
    # Retrieve context
    if book_name:
        retriever = get_retriever(book_name)
        try:
            docs = retriever.get_relevant_documents(query)
        except Exception:
            docs = retriever._get_relevant_documents(query, run_manager=None)
    else:
        docs = vector_store.similarity_search(query, k=4)

    combined = "\n\n".join(d.page_content for d in docs)
    prompt = (
        "Based on the passages below, write a single-sentence moral or lesson that captures the main takeaway. Keep it general and applicable.\n\n"
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


toolbox = [retrieve_context, summarize, moral_creator]