# Devlog #9 — Mixture of Experts & Closing Phase 0

**Date:** June 12, 2025
**Ticket:** THU-11 — Mixtral MoE
**Status:** ✅ Closed | Phase 0 Complete 🌀

---

## What This Session Was

This was the final conceptual checkpoint of Phase 0. No code this time — MoE is an architecture that lives inside the model itself, at the weights level. Building a real MoE implementation would require training a transformer from scratch, which is firmly model training territory — not application layer work. So this session was about understanding *why* the architecture exists, how it works, and what it means for how I pick models for Project Cyclone later.

---

## The Company Analogy That Clicked Everything

Imagine a company with 8 specialized departments — legal, finance, engineering, creative, and so on. When a task comes in, you have two options:

**Option A:** Send the task to all 8 departments. Everyone works on it.

**Option B:** A smart coordinator looks at the task and routes it to only the 2 departments that are actually relevant. The other 6 don't touch it.

Option B is faster, cheaper, and more efficient. That's Mixture of Experts in one analogy.

In a standard transformer, there's a component called the **Feed Forward Network (FFN)** that runs after attention in every transformer block. For every token, the full FFN fires — all parameters, every time. MoE replaces that single FFN with **multiple FFNs called experts**, and a **router** (the smart coordinator) that decides which 2 experts to activate per token. The rest stay idle.

---

## Key Concepts

### Experts
Not individual neurons — full sub-networks, each with their own weights. Mixtral 8x7B has 8 of these, each roughly 7B parameters. Over training, they naturally specialize in different types of patterns and token distributions.

### The Router (Gating Network)
A learned component that looks at the incoming token and outputs a score for each expert. It picks the **top-K** (usually K=2) and routes the token there. The routing decision is made per token, per layer.

### Sparse Activation = The Core Trick
Total parameter count is huge. Compute per token is small. You get the *capacity* of a large model without paying the full *cost* of running one.

Mixtral 8x7B: 8 experts × 7B params = ~56B total parameters. But only 2 experts fire per token, so it runs closer to a 13B model in terms of actual compute. That's the entire value proposition.

### Expert Collapse (and Why It's a Real Problem)
If the router is unconstrained, it gravitates toward a few experts it trusts and ignores the rest. Those ignored experts stop receiving training signal and become useless. You end up with 2 overloaded experts and 6 dead ones.

The fix is an **auxiliary load balancing loss** — a penalty term added during training that forces the router to distribute tokens fairly across all experts. Not something I need to implement, but understanding *why* it exists matters.

---

## Where Mixtral Fits

Mixtral is one of the most well-known open MoE models, released by **Mistral AI** with open weights — meaning it can be run locally. It wasn't the first MoE ever, but it was one of the first transparent, open, high-quality ones. MoE as a pattern has been adopted widely — GPT-4 is rumored to use it, Gemini models use it. It's become the standard approach for scaling efficiently.

---

## Why This Matters for Project Cyclone

Cyclone needs to run locally, on constrained hardware (Ryzen 7 5800HS, 16GB RAM, CPU-only). Model selection is one of the most critical architectural decisions I'll make. Understanding MoE means I now know what "8x7B" actually means — it's not 56B worth of compute per inference. When evaluating which models to run locally for Cyclone, I can look at the active parameter count (what actually fires per token) rather than just the total parameter count. That's the number that determines speed and RAM pressure on my machine.

---

## Phase 0 — Complete

Looking back at what Phase 0 covered:

| Checkpoint | Status |
|---|---|
| RAG | ✅ |
| Transformers | ✅ |
| Neural Networks | ✅ |
| LLMs & Finetuning | ✅ |
| LangChain Agents + Tools | ✅ |
| Embeddings + Vector Search | ✅ |
| ReAct from Scratch | ✅ |
| Mixture of Experts | ✅ |

Eight checkpoints. Nine devlogs. One repo full of things I actually built and understood — not copy-pasted.

The biggest lesson from Phase 0 wasn't any single concept. It was the session before this one — THU-10 — where I built a ReAct agent completely from scratch, hit real bugs, fixed them, and eventually realized the ceiling wasn't my code. It was the model. `qwen2.5:3b` is too small for reliable structured agentic output. That's the kind of insight you only get when you build at the lowest level of abstraction and debug everything by hand. No tutorial gives you that.

---

## What's Next

Phase 1 of Project Cyclone begins.

The foundation is set. The concepts are internalized. Now it's time to start building the actual system — memory, context, proactive behaviour, the whole thing.

🌀

---

*Part of [Project Cyclone](https://github.com/your-repo-here) — a fully local, proactive, emotionally aware personal AI assistant built from scratch.*
