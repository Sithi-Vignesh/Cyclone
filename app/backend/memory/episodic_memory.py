from app.backend.memory.chroma_client import store, retrive
from datetime import datetime


def store_episode(text, speaker, sentiment_score=0.0):
    metadata = {
        "speaker" : speaker,
        "timestamp" : datetime.now().isoformat(),
        "sentiment_score" : sentiment_score
    }
    store(text, metadata, "episodic_memory")

def retrieve_episodes(query, k=5):
    response = retrive(query, "episodic_memory", k)
    return response

def retrieve_personal_facts(query, k=5):
    return retrive(query, "personal_facts", k=k)