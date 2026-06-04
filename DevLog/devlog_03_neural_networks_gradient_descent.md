# Devlog #3 — Neural Networks, Gradient Descent & How AI Actually Learns

**Date:** June 4, 2026
**Phase:** 0 — Concept Sprint (Before Code)
**Status:** Neural Networks + Backpropagation checkpoint ✅ complete

---

## What This Session Was

Still in the concept sprint. Still exactly as planned. Today I went through 3Blue1Brown's Deep Learning playlist — Neural Networks, Gradient Descent, and Backpropagation (intuitively). No code. Just understanding the engine that powers every LLM I'll ever use in Cyclone. By the end, concepts that looked like PhD-level math turned out to be surprisingly simple ideas dressed in scary notation.

---

## Key Concepts Learned

### 1. Neural Networks — Layers, Neurons & Hierarchical Features

A neural network is an attempt to mimic how the human brain works. Neurons are arranged in layers — input layer, hidden layers, output layer. Each layer influences the next. Data flows in from the start, gets processed through the mystery middle, and a prediction comes out the end.

But here's the part that actually clicked: neurons aren't hardcoded to detect specific things. They store **weights** — numbers that say "how much should I care about this input?" The pattern recognition *emerges* from millions of weights being tuned together through training.

The hierarchy builds naturally:
- Early layers detect simple patterns (edges, tones, letters)
- Middle layers combine them into bigger patterns (shapes, syllables)
- Final layers assemble those into meaningful outputs (objects, words)

No single neuron is told what to learn. It figures it out through backpropagation.

---

### 2. Sigmoid vs ReLU — The Vanishing Gradient Problem

Early neural networks used the **sigmoid** activation function to decide whether a neuron fires. It squishes every value between 0 and 1 — looks clean, causes a disaster.

The problem: during backpropagation, error travels backwards through layers as multiplications. Sigmoid outputs are always tiny fractions. Tiny × tiny × tiny × tiny = basically zero. By the time the error reaches the early layers, they receive almost no signal and learn almost nothing. The network goes deaf in its own foundation. This is the **vanishing gradient problem.**

**ReLU** fixes it simply: if the input is positive, pass it through unchanged. If negative, output zero. No squishing. Gradients flow cleanly backwards. Early layers actually learn.

Simple fix. Massive impact. Most modern networks use ReLU or a variant of it.

---

### 3. Gradient Descent — The Blindfolded Hike

Imagine you're blindfolded on a hilly landscape. Your goal is to reach the lowest point in the valley. You can't see anything — but you can feel which direction the ground slopes downward. So you take a small step downhill. Feel again. Step again. Repeat until you hit the bottom.

That's gradient descent.

- **The landscape** = all possible combinations of weights
- **Your position** = the network's current weights
- **The slope** = how much each weight is contributing to the error
- **The step** = nudging each weight slightly to reduce error
- **The valley** = minimum loss — the model is as accurate as it can be

The "gradient" is just the slope. "Descent" is walking downhill. That's the entire idea.

---

### 4. Backpropagation — The Map That Shows Downhill

Gradient descent is the step. Backpropagation is the map.

After every prediction, the network compares its output to the correct answer and measures how wrong it was — this is the **loss.** That error then travels *backwards* through every layer, calculating: "how much did each weight contribute to this mistake?"

Each weight gets nudged slightly in the direction that reduces the error. This happens for every training example. Millions of times. That's how a model learns.

Backpropagation happens once per training example. To train a full model, you need millions of them. Which is exactly why we use **epochs and batch sizes** — now I understand why those parameters exist instead of just copy-pasting them.

---

### 5. Stochastic Gradient Descent — The Drunken Man Walking Downhill

There are two ways to do gradient descent:

**Full batch** — calculate the gradient using the entire dataset before taking one step. Perfectly smooth descent toward the valley. Brutally slow. Impractical at scale.

**Mini-batch (SGD)** — split the data into small batches. Calculate gradient per batch, take a step, repeat. The path to the valley looks like a drunken man stumbling downhill — noisy, slightly erratic — but *dramatically* faster.

The noise isn't always bad though. A perfectly smooth descent can get trapped in a small dip that isn't the true lowest point — a **local minimum.** The noisy jumps of SGD can bounce the model out of those false valleys toward the real bottom.

So the "flaw" is sometimes a feature. That reframing stuck with me.

---

## Why This All Matters for Cyclone

Cyclone will never train a neural network. The weights are already frozen inside whichever local LLM I plug in. But understanding how those weights got there matters enormously:

1. **Hierarchical features explain why context matters so much.** The LLM's early layers built up from simple patterns. What I feed into the prompt at the top shapes everything that flows through those layers. Garbage in, garbage out — but now I understand *why* at an architectural level.

2. **Vanishing gradients explain why deep networks need careful design.** When I'm evaluating which local LLM to use for Cyclone, architecture choices like activation functions and layer depth directly affect quality. I can read those specs now and understand what they mean.

3. **SGD and epochs explain every training config I'll ever read.** Model cards list training details — batch size, learning rate, epochs. These were black boxes before. Now they're readable. I know what tradeoffs the researchers made.

4. **Loss functions are what I'm optimising for indirectly.** When I tune Cyclone's prompts, retrieval quality, and temperature — I'm manually doing what gradient descent does automatically during training. Minimizing bad outputs. Maximizing relevance. Same goal, different method.

---

## What's Next

**Devlog #4 — Let's Build GPT (Karpathy)**

Andrej Karpathy's "Let's build GPT from scratch" is next. Not because I'll build my own LLM — I won't — but because watching the internals assembled line by line in Python will make the architecture concrete instead of abstract. After that, the concept sprint is done.

**Phase 1 begins. First real code of Project Cyclone.**

---

*Built by Sithi Vignesh — CS (AI/ML), VIT Vellore.*
*Project Cyclone: a fully local, proactive, emotionally aware personal AI assistant. The real Jarvis.*
