from app.backend.memory.chroma_client import store, retrive
from datetime import datetime

def store_episode(text, speaker):
    metadata = {
        "speaker" : speaker,
        "timestamp" : datetime.now(),
        "sentiment_score" : 0.0
    }
    store(text, metadata, "episodic_memory")

def retrieve_episodes(query, k=5):
    response = retrive(query, "episodic_memory", k)
    return response