# Devlog #6 — Agents, Tools & Routing: Building a Real Agentic AI System

**Date:** June 9, 2026
**Project:** Cyclone | **Phase:** 0 — Concept Sprint (THU-9)

---

## What happened this session

This session was THU-9 in disguise — it came packaged as an IBM college assignment, but it was exactly what was on the roadmap: LangChain tools, agents, and the ReAct pattern in practice. I built a fully working Smart College Assistant chatbot from scratch — 6 tools, a live agent loop, and multi-tool routing — all running locally with Ollama. By the end of it, I didn't just understand how agents work in theory. I had one running in my terminal.

---

## What I built

A conversational college assistant that handles:

| Tool | What it does |
|---|---|
| Attendance Checker | Takes classes attended + total, returns eligibility status |
| Result Calculator | Takes 5 subject marks, computes average, returns grade + pass/fail |
| Fee Balance | Takes total fee + amount paid, returns pending balance |
| Library Fine Calculator | Takes days late, returns fine amount |
| Hostel Fee Calculator | Takes monthly fee + months stayed, returns total |
| Student Info Finder | Takes a student ID, returns name, branch, year of passing |

All 6 tools are wired into a single ReAct agent. One chatbot loop. Type your query naturally — the agent figures out which tool to call.

---

## Key concepts — in my own words

### How the agent routes to the right tool

This was the first thing that clicked. The agent doesn't follow hardcoded if-else logic like "if the user says attendance, call the attendance tool." Instead, the LLM *reads the docstrings* of all the tools and semantically matches the user's intent to the right one. That's why the docstring matters — it's not just documentation, it's literally how the agent decides what to do. If the docstring is vague, the agent routes wrong. If it's clear, it routes perfectly. That's a wild design — the tool's description *is* the routing logic.

### The `@tool` decorator

This is LangChain's way of converting a plain Python function into something the agent can discover and use. Three things are required for it to work properly:
- The `@tool` decorator itself
- Type hints on the parameters (so the agent knows what to pass in)
- A clear docstring (so the agent knows *when* to use it)

Miss any of those and either the agent won't find the tool or won't know how to call it correctly.

### Why I used a nested dict for student data

For the Student Info tool, I had two options — store each student as a list `["Sithi Vignesh", "CSE AI/ML", 2028]` or as a dict `{"Name": "Sithi Vignesh", "Branch": "CSE AI/ML", ...}`. I went with the dict because when you're returning formatted output, `student["Name"]` is way cleaner than remembering that index 0 is the name. Readability compounds — especially when the agent is reading the output and deciding what to tell the user.

### Return types matter for agents

Early version of the student tool returned a raw dict on success and a string on failure — mismatched return types. The fix was committing to `str` for both cases and formatting the dict values into a readable f-string. The reason: I shouldn't rely on the LLM to interpret an empty dict as "not found." A clear message string is unambiguous. The agent always gets something it can communicate directly to the user.

### Multi-tool queries

The thing that actually impressed me — I threw a single prompt at the agent: *"I attended 80 classes out of 100. My marks are 90, 85, 88, 92 and 95. My course fee is 60000 and I paid 45000. Tell me my attendance status, grade and pending fee."* The agent called three tools in sequence, stitched the results together, and returned a clean structured response. No special configuration. Just the ReAct loop doing its job — reason, act, observe, repeat.

---

## Why this matters for Cyclone

Cyclone is an agentic system at its core. It won't just answer questions — it'll decide what action to take based on context, call the right tool, and respond accordingly. Everything I built today is the exact pattern Cyclone will use:

- **Tool routing via docstrings** → Cyclone's tools (memory retrieval, mood detection, Spotify control, etc.) will be discovered and called the same way
- **ReAct loop** → Cyclone's reasoning engine is this loop — observe the user's state, decide what to do, act, check the result
- **Returning clean strings** → Cyclone's tools need to return responses the LLM can reason about, not raw data structures it has to interpret

Today wasn't just an assignment. It was a dry run of Cyclone's architecture.

---

## What's next

THU-10 — going deeper into the ReAct paper itself, then implementing a more deliberate ReAct agent in LangChain. The goal is to understand what's happening under the hood when the agent "reasons" — not just use it as a black box.

Cyclone gets closer. 🌀
