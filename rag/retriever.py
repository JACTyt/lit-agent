from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from rag.ingest import ensure_books_ingested

DB_PATH = "rag/chroma_db"


def get_retriever(book_name=None):
    try:
        ensure_books_ingested(verbose=False)
    except Exception:
        # Fall back to existing persisted DB if re-ingestion cannot run right now.
        pass

    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(
        persist_directory=DB_PATH,
        embedding_function=embeddings,
    )

    if book_name:
        return vectorstore.as_retriever(
            search_kwargs={
                "k": 4,
                "filter": {"book_name": book_name.lower()},
            }
        )

    return vectorstore.as_retriever(search_kwargs={"k": 4})
