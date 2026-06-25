from app.backend.core.llm import llm
from app.backend.memory.chroma_client import get_all, store, delete_by_topic, clear_episodes
from app.backend.chat.schemas import PersonalFact
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
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

    chain = prompt | llm
    response = chain.invoke({"episodes": str(episodes), "personal_facts": str(personal_facts)})
    
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