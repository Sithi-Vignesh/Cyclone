# Devlog #7 — Embeddings + Vector Search: Hands On

**Date:** June 10, 2026
**Ticket:** THU-8 | **Phase:** 0 — Foundations
**Tags:** `sentence-transformers` `embeddings` `cosine-similarity` `semantic-search` `Project Cyclone`

---

## What happened this session

THU-8 was the embeddings session I'd been putting off — and it turned out to be one of the most satisfying builds so far. No agents, no chains, just math and meaning. I embedded 10 sentences from scratch, implemented cosine similarity by hand (no sklearn, no shortcuts), and built a working semantic search that ranked results by meaning. And somewhere in the middle of it, I accidentally discovered a real limitation of pure semantic search.

---

## What I actually understood

### Embeddings aren't tokens

I walked in thinking embeddings and tokenization were the same thing. They're not. Tokenization breaks a sentence into pieces. Embedding takes those pieces further and compresses the *meaning* of the whole sentence into a fixed list of numbers — 384 of them in this case. The model throws away a lot of information to do that, which means you can never decode an embedding back into the original sentence. It's a one-way door.

### Sentences as points in space

The real insight is *why* you'd want a sentence to be a vector. Once a sentence is a point in multi-dimensional space, sentences with similar meaning end up close to each other. That's not magic — that's what the model was trained to do. And once meaning = position, similarity = distance. That's the whole foundation of semantic search and RAG retrieval.

### Cosine similarity > Euclidean distance

My first instinct was to measure distance between points. That's Euclidean distance — the straight line between two tips. But there's a problem. Take `"I love cats"` and `"I love cats and I love cats and I love cats"` — same meaning, but the second vector is way longer. Euclidean distance would say they're far apart.

Cosine similarity measures the **angle** between vectors instead of the distance between their tips. Same direction = same meaning, regardless of length. The score lands between -1 and 1:
- `1` → identical meaning
- `0` → no relation
- `-1` → opposite meaning

I implemented it fully from scratch:

```python
def dot_product(A, B):
    return sum(a * b for a, b in zip(A, B))

def norm(A):
    return (sum(a * a for a in A)) ** 0.5

def cosine_similarity(A, B):
    return dot_product(A, B) / (norm(A) * norm(B))
```

No library. Just the math.

---

## What I built

10 sentences across three clusters — anime, sports/games, and tech/hardware. Embedded them all with `sentence-transformers/all-MiniLM-L6-v2`, then queried with:

> *"Which laptop does THUNDER use?"*

Results ranked by cosine similarity (ascending):

| Score | Sentence |
|-------|----------|
| -0.056 | i love playing football and basketball |
| 0.017 | me and my friend played split-fiction game a while back |
| 0.054 | the Anime of the year 2025 is Solo Leveling |
| 0.088 | Volleyball in my favorite anime |
| 0.105 | the Anime of the year 2026 is My Hero Academia |
| 0.158 | Haikyuu is a anime based on Volleyball |
| 0.199 | the price of RAMs and Processor have increased exponentially |
| 0.292 | i have played FIFA26 game in my friend's laptop |
| 0.328 | Asus zenbook has Ryzen 5800hs processor |
| **0.475** | **i have Asus Zenbook and my friend has Lenovo LOQ** |

The laptop sentence ranked #1 with 0.475 — and the model had never seen the query before. No keyword match on "Thunder". Pure meaning.

---

## The unexpected finding

Sentence 6 — *"i have played FIFA26 game in my friend's laptop"* — scored 0.292, higher than the processor spec sentence initially. Why? Because the word "laptop" appears in both the query and that sentence. The model isn't purely semantic — word overlap still creates a strong signal in the embedding space.

This is exactly why production RAG systems use **hybrid search** — keyword search + semantic search combined. Pure semantic can miss exact matches. Pure keyword misses meaning. You need both.

I didn't read that anywhere. I noticed it in my own output.

---

## Why this matters for Cyclone

Cyclone's memory system needs to know *which* past context is relevant to retrieve before sending anything to the LLM. I can't send everything — that's too many tokens and too much noise. Cosine similarity over embedded memories is the filter. When Cyclone hears something new, it embeds it, compares it against stored memory vectors, and retrieves only the semantically closest ones.

THU-8 wasn't just a concept exercise. This is the actual retrieval layer I'll wire into Cyclone's memory pipeline.

---

## What's next

**THU-9 is already done** (LangChain Agents — Smart College Assistant with 6 tools, multi-tool chaining, ReAct agent via `langgraph.prebuilt`). That devlog is Devlog #6.

Up next: **THU-10** — reading the original ReAct paper and implementing a deliberate ReAct loop from scratch to understand what's actually happening under the hood when an agent "thinks".

The foundations are almost complete. Phase 1 is close. 🌀

---

*Part of Project Cyclone — a fully local, proactive, emotionally aware personal AI assistant.*
