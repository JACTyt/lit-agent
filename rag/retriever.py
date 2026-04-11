from langchain_chroma import Chroma
from agent.llm_provider import get_embeddings
from rag.ingest import ensure_books_ingested
from rag.constants import DB_PATH, COLLECTION_NAME


def get_retriever(book_name=None):
    try:
        ensure_books_ingested(verbose=False)
    except Exception:
        # Fall back to existing persisted DB if re-ingestion cannot run right now.
        pass

    embeddings = get_embeddings()
    vectorstore = Chroma(
        persist_directory=DB_PATH,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )

    if book_name:
        return vectorstore.as_retriever(
            search_kwargs={
                "k": 4,
                "filter": {"book_name": book_name.lower()},
            }
        )

    return vectorstore.as_retriever(search_kwargs={"k": 4})
