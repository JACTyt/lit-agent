from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import chromadb

DB_PATH = "rag/chroma_db"
COLLECTION_NAME = "books_collection"

client = chromadb.PersistentClient(path=DB_PATH)

# List all collections
print("Collections:", client.list_collections())

# Access your collection
collection = client.get_collection(name=COLLECTION_NAME)
print("Collection name:", collection.name)

# Count vectors
print("Number of documents:", collection.count())

# Get first 5 documents properly
results = collection.get()

documents = results['documents']      # list of document strings
metadatas = results['metadatas']      # list of metadata dicts

for i in range(len(documents)):
    print(f"Doc {i}:")
    print("Book:", metadatas[i]["book_name"])
    print("Text:", documents[i][:200])  # first 200 chars
    print("-----")