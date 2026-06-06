# Devlog #5 — How LLMs Actually Work (And Why Pretraining Isn't Enough)

**Date:** June 6, 2026
**Phase:** 0 — Concept Sprint (Before Code)
**Status:** LLM internals + finetuning checkpoint ✅ complete

---

## What This Session Was

This session was about closing the loop on how LLMs go from raw pretrained models to actual useful assistants. I went through 3Blue1Brown's *LLMs Explained* and the first stretch of Andrej Karpathy's *Let's Build GPT from Scratch* — and a lot of things I'd learned in isolation (transformers, attention, neural nets) finally snapped together into one clear picture.

---

## Key Concepts Learned

### 1. Pretraining — The Raw, Unfiltered Brain

A pretrained LLM is trained on billions of tokens from the internet with one single goal: **predict the next token**. That's it. No instructions, no personality, no sense of when to stop.

So if you ask it *"What is the capital of France?"* — it's not trying to answer you. It's trying to complete the pattern. It might say *"Paris, and the capital of Germany is Berlin, and the capital of Spain is Madrid..."* and just keep going. Because that's what internet text looks like. It has zero concept of being an assistant.

The model at this stage is basically a very powerful sentence completion machine — it knows an insane amount about the world, but it has no idea how to behave.

### 2. The Transformer Under the Hood (Karpathy's View)

Watching Karpathy build it from scratch made the architecture feel real. The flow is:

- Raw text gets broken into **tokens**
- Tokens become **embeddings** — vectors that carry meaning
- **Attention layers** let every token look at every other token and decide what's relevant
- **MLP layers** process and transform that information
- **Softmax** converts the final output into probabilities over the entire vocabulary
- The token with the highest probability gets picked — and the loop repeats

Temperature sits right here at the softmax stage. Low temperature = the model always picks the most probable token (safe, predictable). High temperature = it takes more risks (creative, sometimes chaotic).

### 3. RLHF — Teaching the Model to Behave

This is the bridge between *raw pretrained model* and *useful AI assistant*. RLHF stands for **Reinforcement Learning from Human Feedback**.

The process: humans review the model's outputs and flag which ones are good and which are bad. The model gets rewarded for good answers and penalized for bad ones. Over thousands of iterations, it gets optimized toward one new objective — **be helpful, be accurate, stop when done**.

The key insight here: finetuning doesn't change *what the model knows*. The knowledge was baked in during pretraining. Finetuning changes **how the model behaves**. It's the difference between a genius who rambles endlessly and a genius who actually answers your question.

This is how Claude, GPT, and Gemini all work under the hood.

### 4. Why GPUs Matter

Training these models means running the same matrix multiplications billions of times — updating weights across millions of parameters on massive datasets. CPUs are sequential. GPUs are built for parallel computation, meaning they can handle thousands of these operations simultaneously. Without GPUs, modern LLM training would be practically impossible at scale.

---

## Why This Matters for Cyclone

- **Pretraining vs finetuning clarity** — Cyclone will run on top of a pretrained + finetuned model. Understanding this separation means I know exactly what the model brings to the table and what I need to engineer around it.
- **Attention = Cyclone's context awareness** — Every time Cyclone processes a conversation, attention is what lets it connect *"you mentioned stress earlier"* to *"you just opened Spotify."* That's the foundation of proactive behaviour.
- **RLHF = why the base model isn't enough** — If I ever consider local finetuning for Cyclone's personality layer, this is the mechanism. Not just prompting — actual behaviour shaping.
- **Temperature** — Cyclone needs to be precise for memory retrieval and task execution, but slightly creative for conversation. Temperature is the knob that controls this.

---

## What's Next

Phase 0 continues. THU-8 is next — hands-on embeddings. Run sentence-transformers locally, embed 10 sentences, compute cosine similarity manually. First real code of the entire Cyclone journey. The theory ends. The build begins. 😤

---

*Built by Sithi Vignesh — CS (AI/ML), VIT Vellore.*
*Project Cyclone: a fully local, proactive, emotionally aware personal AI assistant. The real Jarvis.*
