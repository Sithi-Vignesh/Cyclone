# Devlog #2 — Transformers, Attention & How LLMs Actually Think

**Date:** June 3, 2026
**Phase:** 0 — Concept Sprint (Before Code)
**Status:** Transformers checkpoint ✅ complete

---

## What This Session Was

Still no code. Still exactly as planned. Today I went deeper into the actual engine powering every LLM — the Transformer architecture. Watched 3Blue1Brown's Deep Learning Chapter 5 and spent the session breaking down what I saw. Attention, backpropagation, probability-based generation — and the one realization that genuinely stunned me. This isn't magic. It's math that got really, really good.

---

## Key Concepts Learned

### 1. The Realization That Changed Everything

AI doesn't *know* anything. It *predicts.*

Every word Cyclone will ever say to me is the result of a probability distribution — the model calculating "given everything before this, what token comes next?" and picking the most likely one. There's no understanding hiding behind the curtain. Just math that learned patterns from billions of human sentences so well that it *feels* like understanding.

This matters more than it sounds. It means I should never blindly trust Cyclone's outputs. It means hallucinations aren't bugs — they're the model being confidently wrong because the probability pointed that way. And it means the value I add as the builder is in the *context* I give the model — which is exactly what RAG is for.

---

### 2. The Transformer — Big Picture Flow

Before diving into the pieces, here's the skeleton:

```
Raw text
   ↓
Tokenization — text split into tokens
   ↓
Embedding — each token becomes a vector (meaning as numbers)
   ↓
Attention + MLP block (repeated many times)
   ↓
Final prediction matrix
   ↓
Softmax normalization → probability distribution
   ↓
Output token selected (based on temperature)
```

Everything interesting happens inside that **Attention + MLP cycle.** The rest is plumbing.

---

### 3. Attention — Words Looking at Each Other

This is the part that makes Transformers actually intelligent.

Take the sentence: *"The bank by the river was muddy."*

The word "bank" alone means nothing definitive — financial bank or riverbank? Attention is the mechanism that figures it out. Every word looks at every other word in the sentence and asks: *"How relevant are you to understanding me?"*

"River" is highly relevant to "bank." So "bank's" vector gets pulled toward the riverbank meaning. By the time Attention finishes, "bank" has absorbed context from its entire surroundings.

Under the hood, this happens through three components per word:

- **Q (Query)** — "What context am I looking for?"
- **K (Key)** — "What do I represent?"
- **V (Value)** — "What do I contribute to others?"

Every word computes its Query against every other word's Key. High match → that word's Value flows in and updates the meaning vector. This is called **Q, K, V Attention** and it's the core of every modern LLM.

The cycle repeats through multiple layers — each pass refining the meaning further. By the end, every token's vector has been shaped by the full context of the sentence. That's how Transformers handle nuance, ambiguity, and long-range relationships between words.

---

### 4. Backpropagation — The Dr. Strange Learning Loop

Here's where I had my second big realization of the session.

Training a model is basically Dr. Strange with the Time Stone.

The model makes a prediction → compares it to the correct answer → measures how wrong it was (this is called the **loss**) → then traces *backwards* through every decision it made, asking "which step contributed most to this mistake?" → nudges each weight slightly in the right direction.

It doesn't redo the whole forward pass. It just adjusts each parameter by a tiny amount — called the **learning rate** — so the next prediction is marginally better. Repeat this millions of times across billions of examples and you get a model that seems to understand language.

The formal name for that backward trace is **backpropagation.** The nudging process is **gradient descent.**

**Critical distinction for Cyclone:** I am not building a model that trains. Cyclone will *use* a model that was already trained this way. Backpropagation is done. The weights are frozen. My job is to build the layer on top — memory, personality, proactive behaviour — not to touch the brain itself.

---

### 5. Softmax & Temperature — Controlling the Randomness

After the Transformer produces its final prediction matrix, the raw numbers (called logits) get converted into a proper probability distribution using the **Softmax function.** Every possible next token gets a probability score that sums to 1.

Then **temperature** controls how Cyclone samples from that distribution:

- **Low temperature** → picks the highest probability token almost always → more predictable, focused responses
- **High temperature** → spreads probability across more options → more creative, sometimes surprising outputs

For Cyclone's personality — warm but reliable — I'll want a low-to-mid temperature. High enough to feel human, low enough to stay coherent.

---

## Why This All Matters for Cyclone

Cyclone is **not** an LLM. Cyclone is an application built *on top* of one.

Understanding Transformers matters because:

1. **Attention explains why context window management is critical.** The model attends to everything in its context. Garbage in, garbage out. What I inject into the prompt (via RAG) directly shapes what Cyclone says.

2. **Probability explains why I need discernment.** Cyclone will sometimes be confidently wrong. I need to build guardrails and teach myself to evaluate outputs critically — not just trust the fluency.

3. **Temperature is a tuning knob I'll actually use.** When I'm configuring the local LLM for Cyclone, temperature will be one of the first things I calibrate for her personality.

4. **Backpropagation is done for me.** I don't need to train anything. The hard work is complete. My job starts at the application layer — and that's exactly where the interesting problems are.

---

## What's Next

**Devlog #3 — Let's Build GPT (Karpathy)**

Before touching any Cyclone code, I'm watching Andrej Karpathy's "Let's build GPT from scratch." Not because I'll build my own LLM — I won't — but because seeing the internals assembled line by line will make me a significantly better application builder. Understanding the engine makes you a better driver.

After that — we start Phase 1. The first real code of Project Cyclone.

---

*Built by Sithi Vignesh — CS (AI/ML), VIT Vellore.*
*Project Cyclone: a fully local, proactive, emotionally aware personal AI assistant. The real Jarvis.*
