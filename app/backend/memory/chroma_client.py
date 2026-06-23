import chromadb
import uuid
from sentence_transformers import SentenceTransformer

embedder = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient("./chroma_data/")

collections = {
    "core_memory": client.get_or_create_collection("core_memory"),
    "episodic_memory": client.get_or_create_collection("episodic_memory"),
    "semantic_summaries": client.get_or_create_collection("semantic_summaries")
}

def embed(text):
    return embedder.encode(text).tolist()

def clear_episodes():
    collection = collections["episodic_memory"]
    all_ids = collection.get()["ids"]
    if all_ids:
        collection.delete(ids=all_ids)
        
def store(text, metadata, collection_name):
    embedding = embed(text)
    collections[collection_name].add(
        documents=text,
        embeddings=embedding,
        metadatas=metadata,
        ids=[str(uuid.uuid4())]
    )

def retrive(query, collection_name,k):
    query_embeddings = embed(query)
    ans = collections[collection_name].query(
        query_embeddings = query_embeddings,
        n_results=k
    )
    return ans