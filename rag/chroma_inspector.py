from rag.constants import DB_PATH, COLLECTION_NAME
import chromadb


if __name__ == "__main__":
    from agent.llm_provider import get_embeddings  # noqa: F401 — ensures provider env is loaded

    client = chromadb.PersistentClient(path=DB_PATH)

    print("Collections:", client.list_collections())

    collection = client.get_collection(name=COLLECTION_NAME)
    print("Collection name:", collection.name)
    print("Number of documents:", collection.count())

    results = collection.get()
    documents = results["documents"]
    metadatas = results["metadatas"]

    for i in range(len(documents)):
        print(f"Doc {i}:")
        print("Book:", metadatas[i]["book_name"])
        print("Text:", documents[i][:200])
        print("-----")
