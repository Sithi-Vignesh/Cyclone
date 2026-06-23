from langchain_core.prompts import ChatPromptTemplate
from app.backend.core.llm import llm
from app.backend.memory.chroma_client import store, retrive, clear_episodes

def generate_summary(episodes):
    prompt = ChatPromptTemplate.from_template("""
    Using this context: {episodes}
    
    Generate a brief yet detailed summary of this chat.
    Use semantic compression, not transcription.
    Capture what happened and why it mattered, not the raw content.
    Extract intent, emotion, plans, key facts — discard transactional back-and-forth.
    """)
    
    chain = prompt | llm
    response = chain.invoke({"episodes": episodes})
    return response.content

def save_summary(summary_text, start_time, end_time, trigger_type):
    metadata = {
        "start_time": start_time,
        "end_time": end_time,
        "trigger_type": trigger_type
    }
    store(summary_text, metadata, "semantic_summaries")
    clear_episodes()

def retrieve_summary(query, k=5):
    return retrive(query, "semantic_summaries", k)