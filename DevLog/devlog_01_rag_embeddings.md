# Devlog #1 — RAG, Embeddings & The Memory Brain of Cyclone

**Date:** June 2, 2026
**Phase:** 0 — Concept Sprint (Before Code)
**Status:** RAG checkpoint ✅ complete

---

## What This Session Was

Before writing a single line of code for Cyclone, I committed to understanding the *why* behind every architectural decision. Today was about the most important one — memory. Specifically: why plain memory fails, what embeddings actually are, and how RAG turns a forgetful LLM into something that genuinely knows you. No code today. Just deep thinking.

---

## Key Concepts Learned

### 1. Embeddings — Meaning as Numbers

Text gets converted into vectors — lists of numbers like `[0.23, -0.81, 0.44...]` — where similar meanings land close together in vector space.

My mental model: imagine a 3D space where dimension 1 = dinosaurs, dimension 2 = rollercoasters, dimension 3 = books. The word "dino-coaster" would map to `[0.9, 0.9, 0.1]` — close to dinosaurs and rollercoasters, far from books. Real embeddings do this across 384 or 1536 dimensions instead of 3, capturing nuance we can't visualise but the math handles perfectly.

The key insight: "exam" and "test" end up close together not because someone hardcoded a synonym list — but because the model trained on billions of sentences where both words appeared in the same contexts. It learned meaning from human usage patterns.

**Why it matters for Cyclone:** When I tell her "I have an exam Friday" and later ask "how did my test go", she needs to connect those two statements. Exact word matching fails completely here. Embeddings make this trivial.

---

### 2. Why Plain Memory Fails

If Cyclone stored every message as raw text in a normal list and searched through it word by word:

- **Semantic gap** — "stressed" and "nervous" are different strings. Plain search misses the connection entirely
- **Speed** — scanning thousands of messages one by one is brutally slow at scale
- **Storage** — raw text of every conversation across months gets heavy fast

Three separate problems. All three solved by the same solution: vector storage + semantic retrieval.

---

### 3. RAG — The Full Loop

**RAG = Retrieval Augmented Generation.**

The flow:

```
Your message
     ↓
Embed the query into a vector
     ↓
Search ChromaDB for top-k semantically similar memories
     ↓
Inject retrieved memories into the LLM prompt (augmentation)
     ↓
LLM generates a response that *knows* your context
```

The analogy that made this click for me:

> **Person A** (ChromaDB) — stores everything you've ever told Cyclone. Can retrieve relevant facts fast. But can't explain, reason, or respond meaningfully.
>
> **Person B** (the LLM) — brilliant at understanding and responding. But has zero memory of its own — forgets everything between sessions.
>
> RAG is the handshake between them. A finds the relevant memories, hands them to B, and B gives you an answer that feels like Cyclone actually knows you.

Neither A nor B alone is Cyclone. Together, they are.

---

### 4. What Cyclone Should Remember vs Forget

Not everything deserves to be stored. Humans don't remember what they ate every day — but they remember patterns. Cyclone should work the same way.

| Message | Store? | Why |
|---|---|---|
| "Hey Cyclone" | ❌ | Wake call — zero information |
| "I'm really stressed lately" | ✅ | Emotional state — future reference |
| "What's 2+2" | ❌ | Stateless query — no personal context |
| "I haven't been sleeping well" | ✅ | Personal pattern — health signal |
| "Open Spotify" (after stress message) | ✅ | Behaviour link — Thunder stressed → listens to music |

That last one is actually a feature I want to build: **contextual behaviour linking.** If Cyclone notices I open Spotify every time I'm stressed, she should learn that pattern and eventually ask "rough day?" when I reach for it.

---

### 5. The Memory Filter — How Cyclone Decides What to Store

Cyclone needs to automatically classify incoming messages as worth storing or not. I evaluated three approaches:

**Option 1 — Train a custom classifier model**
Requires labelled data, training pipeline, separate maintenance. Overkill for this problem. Rejected.

**Option 2 — Ask the LLM to classify every message**
Clean logic, but burns tokens on every single message just to make a storage decision. On free-tier APIs, this is unsustainable. Rejected.

**Option 3 — Embedding similarity scoring**
Embed the incoming message. Check cosine similarity against known "important" topic clusters (emotions, events, personal facts). High similarity score → store. Low score → forget.

Fast, lightweight, no extra API calls, scales cleanly into V2 and V3. **Selected.**

---

### 6. Chunking — Slicing for Precision

When storing large content (documents, long messages, notes), dumping everything as one giant block destroys retrieval quality. If you store 10 pages of notes as a single vector, searching for "backpropagation" retrieves all 10 pages — flooding the LLM with irrelevant context.

The solution: cut content into smaller, meaningful pieces before embedding.

- **Min chunk size** — a single message without context loses meaning. Neighbouring turns need to be included
- **Max chunk size** — a single massive message needs splitting for retrieval to stay precise
- **Overlap** — neighbouring chunks share a few lines so meaning doesn't get severed at the cut point

For Cyclone's conversation memory, individual messages are natural chunks — but with context windows around them for coherence.

---

## Why This All Matters for Cyclone

The exam check-in scenario — Cyclone proactively asking "how did your ML exam go?" after it ends — only works if she:

1. Stored the exam details semantically (not just the exact words)
2. Retrieved them at the right moment based on meaning, not keyword match
3. Injected that context into the LLM before generating the check-in message

Every concept I learned today is a direct building block of that one feature. This isn't abstract theory — it's the architecture of something I'm actually going to build.

---

## What's Next

**Devlog #2 — Transformers & Attention**

Before writing any code, I'm going deep on how Transformers actually work — the attention mechanism, why it changed everything, and what it means for the LLM sitting at the heart of Cyclone. Watching 3Blue1Brown's Attention series and Andrej Karpathy's "Let's build GPT" next.

---

*Built by Sithi Vignesh — CS (AI/ML), VIT Vellore.*
*Project Cyclone: a fully local, proactive, emotionally aware personal AI assistant. The real Jarvis.*
