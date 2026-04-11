import os
import json
import shutil
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from agent.llm_provider import get_embeddings
from langchain_chroma import Chroma
import chromadb
from dotenv import load_dotenv

load_dotenv()  # load OPENAI_API_KEY from .env if needed

BOOKS_DIR = "books/"
DB_PATH = "rag/chroma_db"
COLLECTION_NAME = "books_collection"
STATE_FILENAME = "ingestion_state.json"


def resolve_books_dir(books_dir: str | None = None) -> str:
    """Pick the preferred source directory for books.

    Preference order:
    1) explicit argument
    2) library/
    3) books/
    """
    if books_dir:
        return books_dir
    if os.path.isdir("library"):
        return "library"
    return BOOKS_DIR


def _snapshot_books(books_dir: str) -> dict:
    """Return a stable snapshot of .txt files for change detection."""
    files = {}
    if not os.path.isdir(books_dir):
        return files

    for filename in sorted(os.listdir(books_dir)):
        if not filename.endswith(".txt"):
            continue
        path = os.path.join(books_dir, filename)
        if not os.path.isfile(path):
            continue
        stat = os.stat(path)
        files[filename] = {
            "size": stat.st_size,
            "mtime": int(stat.st_mtime),
        }
    return files


def _state_path(db_path: str = DB_PATH) -> str:
    return os.path.join(db_path, STATE_FILENAME)


def _load_state(db_path: str = DB_PATH) -> dict:
    path = _state_path(db_path)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_state(state: dict, db_path: str = DB_PATH) -> None:
    os.makedirs(db_path, exist_ok=True)
    with open(_state_path(db_path), "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def needs_reingest(books_dir: str | None = None, db_path: str = DB_PATH) -> tuple[bool, str, str]:
    """Check whether the current books directory differs from indexed state."""
    resolved_books_dir = resolve_books_dir(books_dir)
    current_snapshot = _snapshot_books(resolved_books_dir)
    state = _load_state(db_path)

    if not os.path.isdir(db_path):
        return True, "Vector store directory is missing.", resolved_books_dir
    if not current_snapshot:
        return False, "No .txt files found to ingest.", resolved_books_dir

    previous_snapshot = state.get("files", {})
    previous_books_dir = state.get("books_dir")

    if previous_books_dir != resolved_books_dir:
        return True, "Books directory changed.", resolved_books_dir
    if previous_snapshot != current_snapshot:
        return True, "Detected new/updated/removed book files.", resolved_books_dir

    return False, "Ingestion is already up to date.", resolved_books_dir


def ensure_books_ingested(books_dir: str | None = None, db_path: str = DB_PATH, collection_name: str = COLLECTION_NAME, verbose: bool = True) -> dict:
    """Ensure vector DB is in sync with source books and re-ingest only when needed."""
    should_reingest, reason, resolved_books_dir = needs_reingest(books_dir=books_dir, db_path=db_path)

    if not should_reingest:
        return {"ingested": False, "reason": reason, "books_dir": resolved_books_dir, "vector_count": None}

    vectorstore, vector_count = ingest_books(
        books_dir=resolved_books_dir,
        db_path=db_path,
        collection_name=collection_name,
        verbose=verbose,
    )
    return {
        "ingested": True,
        "reason": reason,
        "books_dir": resolved_books_dir,
        "vector_count": vector_count,
    }


def ingest_books(books_dir: str = BOOKS_DIR, db_path: str = DB_PATH, collection_name: str = COLLECTION_NAME, verbose: bool = True) -> tuple[Chroma, int]:
    """
    Ingest all books from a directory into ChromaDB.
    
    Args:
        books_dir: Directory containing .txt files to ingest
        db_path: Path where ChromaDB should be persisted
        collection_name: Name of the ChromaDB collection
        verbose: Whether to print progress messages
        
    Returns:
        Tuple of (vectorstore, document_count)
    """
    books_dir = resolve_books_dir(books_dir)

    # Delete old DB to avoid leftover bad chunks
    shutil.rmtree(db_path, ignore_errors=True)
    
    all_docs = []
    
    # Small chunk size for short stories
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )
    
    if not os.path.isdir(books_dir):
        raise FileNotFoundError(f"Books directory not found: {books_dir}")

    for filename in os.listdir(books_dir):
        if filename.endswith(".txt"):
            path = os.path.join(books_dir, filename)
            
            try:
                loader = TextLoader(path, encoding="utf-8")
                docs = loader.load()  # returns Document objects
                
                # Split the Document into chunks (returns Document objects)
                chunks = splitter.split_documents(docs)
                book_name_clean = os.path.splitext(filename)[0]
                
                # Add book metadata
                for chunk in chunks:
                    chunk.metadata["book_name"] = book_name_clean
                    chunk.metadata["source"] = path
                
                all_docs.extend(chunks)
                if verbose:
                    print(f"{filename}: {len(chunks)} chunks created")
            except Exception as e:
                if verbose:
                    print(f"Error processing {filename}: {e}")
                continue
    
    # Initialize embeddings
    embeddings = get_embeddings()
    
    # Create Chroma vectorstore and persist
    vectorstore = Chroma.from_documents(
        documents=all_docs,
        embedding=embeddings,
        persist_directory=db_path,
        collection_name=collection_name
    )
    
    vector_count = vectorstore._collection.count()

    _save_state(
        {
            "books_dir": books_dir,
            "files": _snapshot_books(books_dir),
            "vector_count": vector_count,
            "collection_name": collection_name,
        },
        db_path=db_path,
    )

    if verbose:
        print("All books ingested successfully!")
        print("Vector count:", vector_count)
    
    return vectorstore, vector_count


if __name__ == "__main__":
    status = ensure_books_ingested(verbose=True)
    if status["ingested"]:
        print(f"Auto-ingest completed from '{status['books_dir']}' with {status['vector_count']} vectors.")
    else:
        print(status["reason"])