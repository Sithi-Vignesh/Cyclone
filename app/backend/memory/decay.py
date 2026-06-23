import math
from datetime import datetime

LAMBDA = 0.01

def apply_decay(results):
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    
    scored = []
    for doc, meta, distance in zip(documents, metadatas, distances):
        similarity = 1 - distance
        timestamp = datetime.fromisoformat(meta["timestamp"])
        hours_elapsed = (datetime.now() - timestamp).total_seconds() / 3600
        decayed_score = similarity * math.exp(-LAMBDA * hours_elapsed)
        scored.append({"document": doc, "score": decayed_score, "metadata": meta})
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored