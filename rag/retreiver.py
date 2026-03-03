from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

DB_PATH = "rag/chroma_db"

def get_retriever(book_name=None):
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(
        persist_directory=DB_PATH,
        embedding_function=embeddings
    )

    # Return the retriever
    if book_name:
        return vectorstore.as_retriever(
            search_kwargs={
                "k": 4,
                "filter": {"book_name": book_name.lower()}
            }
        )

    return vectorstore.as_retriever(search_kwargs={"k": 4})