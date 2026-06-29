from app.backend.core.llm import invoke_with_rotation, build_llms
import app.backend.core.llm as llm_module
from app.backend.memory.chroma_client import get_all, store, delete_by_topic, clear_episodes
from app.backend.chat.schemas import PersonalFact
from langchain_core.prompts import ChatPromptTemplate
from openai import RateLimitError
from app.backend.config.settings import OPENROUTER_API_KEYS
import json
import os

THUNDER_MD_PATH = os.path.join(os.path.dirname(__file__), "../data/thunder.md")

def consolidate_memories():
    episodes = get_all("episodic_memory")
    personal_facts = get_all("personal_facts")

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are Cyclone's memory consolidation engine.
    Extract personal facts about Thunder from the episodes.
    Compare with existing personal facts before classifying.

    Rules:
    - Field names must be exactly: "content", "topic", "action_type" — no other names.
    - topic must be specific (e.g. "volleyball", "learning_style", "interests", "football") — NEVER just "Thunder"
    - If a fact with the same topic already exists in existing facts, classify as "overwrite"
    - If it's genuinely new information, classify as "add"
    - "update" is for partial changes to an existing fact
    - Return ONLY a valid JSON list. No explanation. No markdown. No backticks."""),
        ("human", "Episodes:\n{episodes}\n\nExisting facts:\n{personal_facts}")
    ])

    total_keys = len(OPENROUTER_API_KEYS)
    attempts = 0
    response = None
    while attempts < total_keys:
        try:
            chain = prompt | llm_module.llm
            response = chain.invoke({"episodes": str(episodes), "personal_facts": str(personal_facts)})
            break
        except RateLimitError:
            llm_module.current_key_index = (llm_module.current_key_index + 1) % total_keys
            build_llms(OPENROUTER_API_KEYS[llm_module.current_key_index])
            attempts += 1

    if response is None:
        print("All API keys exhausted during consolidation. Skipping.")
        return

    facts = json.loads(response.content)

    for fact in facts:
        validated = PersonalFact(**fact)
        if validated.action_type == "overwrite":
            delete_by_topic(validated.topic, "personal_facts")
        store(validated.content, {"topic": validated.topic, "action_type": validated.action_type}, "personal_facts")

    update_thunder_md(facts)
    clear_episodes()

def update_thunder_md(facts):
    os.makedirs(os.path.dirname(THUNDER_MD_PATH), exist_ok=True)
    with open(THUNDER_MD_PATH, "a", encoding="utf-8") as f:
        for fact in facts:
            f.write(f"- [{fact['topic']}] {fact['content']}\n")