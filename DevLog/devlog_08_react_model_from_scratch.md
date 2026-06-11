# Devlog #8 — Building ReAct from Scratch (THU-10)

**Date:** June 11, 2025
**Ticket:** THU-10
**Repo:** Agentic-AI-Practice

---

## What happened this session

This session was about going deeper than just *using* ReAct — I built the entire agent loop from scratch, wire by wire, without LangChain doing any of the heavy lifting. No `create_react_agent`, no abstractions. Just Python, Ollama, and a while loop. The goal was to actually *internalize* the reasoning loop, not just call it as a library function.

---

## What I already had coming in

From the previous session (THU-9), I had the concepts locked:

- **ReAct solves two problems:** CoT hallucinates in a vacuum (no external verification), and Act-only makes reactive mistakes (no reasoning). ReAct combines both — you think, then act, then observe, then think again.
- **The loop:** Thought → Action → Observation → repeat until Final Answer
- **Thought = LLM, Action = Tools, Observation = tool's return value fed back to the LLM**
- **Stop condition:** check for `"Final Answer"` string in LLM output
- **Tool router:** plain Python dict mapping string names to actual functions
- **Message history:** list of `{"role": ..., "content": ...}` dicts that grows each iteration

---

## What I built this session

### The Tool Router

Started with two dummy tools — `get_weather` and `get_game_price` — backed by simple Python dicts. The key insight: the tool router is just a dict. `tool_router["get_weather"]` *is* the function. So calling `tool_router[tool](arg)` is all it takes to route dynamically.

```python
tool_router = {
    "get_weather": get_weather,
    "get_game_price": get_game_price
}
```

### The Parsing Block

The LLM outputs something like:
```
THOUGHT: I need to get the weather for Chennai.
ACTION: get_weather(chennai)
```

I needed to extract `get_weather` and `chennai` from that string. My approach:

1. Split `llm_output` by `"\n"` to get individual lines
2. Find the line that `startswith("ACTION:")`
3. Split that line on `"("` → gives `["ACTION: get_weather", "chennai)"]`
4. Split the first part on spaces → grab index `[1]` for the tool name
5. Slice `[:-1]` on the second part to drop the `)`
6. `.strip('"').lower()` to clean quotes and normalize case

```python
x = llm_output.split("\n")
for y in x:
    if y.startswith("ACTION:"):
        z = y.split("(")
        tool = z[0].split()[1]
        arg = z[1][:-1].strip('"').lower()
```

### The Full Loop

The outer `while True` handles multi-turn conversation. The inner `while True` is the ReAct loop — it keeps calling the LLM, parsing output, executing tools, injecting observations, until the LLM says `FINAL ANSWER`.

```python
while True:
    user_input = input("You: ")
    context_window.append({"role": "user", "content": user_input})
    while True:
        response = ollama.chat(model="qwen2.5:3b", messages=context_window)
        llm_output = response["message"]["content"]
        context_window.append({"role": "assistant", "content": llm_output})

        if "ACTION" in llm_output.upper():
            x = llm_output.split("\n")
            for y in x:
                if y.startswith("ACTION:"):
                    z = y.split("(")
                    tool = z[0].split()[1]
                    arg = z[1][:-1].strip('"').lower()
                    if tool in tool_router:
                        result = tool_router[tool](arg)
                        context_window.append({"role": "user", "content": result})

        if "FINAL ANSWER" in llm_output.upper():
            print(llm_output)
            break

    if "FINAL ANSWER" in llm_output.upper():
        break
```

Key design decisions I made along the way:

- **Observations are injected as `"user"` role** — because there's no "environment" role. The environment reports back as if it's the user feeding info in.
- **LLM output always appended as assistant immediately** — so the model sees its own reasoning in the next iteration. Skipping this broke the context.
- **`checkTool()` guard** — if the LLM hallucinates a fake tool name, we skip the call instead of crashing with a `KeyError`.

---

## The bugs I hit and fixed

**Bug 1 — KeyError: 'i'**
I was splitting the entire `llm_output` on spaces instead of isolating the ACTION line first. `y[1]` was picking up `'i'` from the THOUGHT line. Fixed by finding the specific line that starts with `"ACTION:"` first.

**Bug 2 — Wrong arg values**
The LLM was passing `"Chennai"` (with quotes, capital C) but my dict key was `"chennai"`. Fixed with `.strip('"').lower()`.

**Bug 3 — Double append**
The outer loop was re-appending `llm_output` as assistant after the inner loop already did it. Cleaned up by removing the redundant lines from the outer loop.

**Bug 4 — LLM hallucinating observations**
`qwen2.5:3b` kept completing the full THOUGHT → ACTION → OBSERVATION → FINAL ANSWER cycle in one shot instead of pausing after ACTION. This is a small model limitation — it's too eager to complete the pattern. Fixed partially through prompt engineering (removing `tool_call()` wrapper from the format, adding concrete examples, explicit "stop after ACTION" instruction).

---

## The honest engineering takeaway

`qwen2.5:3b` is too small to reliably follow strict agentic output formats. It gets the idea but drifts — hallucinating observations, wrapping calls in `tool_call()`, completing the whole loop in one shot. The engineering is solid; the weak link is model size.

This is a real Cyclone architecture insight: **local small models work for reasoning, but structured multi-step agentic protocols need either a bigger model or a tighter harness** (stop tokens, grammar-constrained decoding, etc.). Something to design around in Phase 1.

---

## Why this matters for Project Cyclone

Cyclone's memory and tool system will run exactly this loop — but at a much larger scale. When Cyclone detects stress and decides to open Spotify, that decision will go through a reasoning loop just like this one:

- **Thought:** I detected elevated stress signals
- **Action:** query_memory(user_patterns)
- **Observation:** Thunder usually listens to lo-fi when stressed
- **Action:** open_spotify(lo-fi playlist)
- **Final Answer:** done

Building this from scratch means I understand every layer of that loop. No black boxes.

---

## What's next

THU-11 — Mixtral MoE. After that, Phase 0 closes and Phase 1 of Project Cyclone begins. 🌀
