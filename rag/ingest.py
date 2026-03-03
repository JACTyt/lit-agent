import os
import shutil
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import chromadb
from dotenv import load_dotenv

load_dotenv()  # load OPENAI_API_KEY from .env if needed

BOOKS_DIR = "books/"
DB_PATH = "rag/chroma_db"
COLLECTION_NAME = "books_collection"

# Delete old DB to avoid leftover bad chunks
shutil.rmtree(DB_PATH, ignore_errors=True)

all_docs = []

# Small chunk size for short stories
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)

for filename in os.listdir(BOOKS_DIR):
    if filename.endswith(".txt"):
        path = os.path.join(BOOKS_DIR, filename)

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
        print(f"{filename}: {len(chunks)} chunks created")

# Initialize embeddings
embeddings = OpenAIEmbeddings()

# Create Chroma vectorstore and persist
vectorstore = Chroma.from_documents(
    documents=all_docs,
    embedding=embeddings,
    persist_directory=DB_PATH,
    collection_name=COLLECTION_NAME
)

print("All books ingested successfully!")
print("Vector count:", vectorstore._collection.count())