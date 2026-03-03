from langchain.tools import tool
from rag.retreiver import get_retriever
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

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

toolbox = [retrieve_context]