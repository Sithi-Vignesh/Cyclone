from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from app.backend.core.llm import llm
from app.backend.prompts.system_prompt import system_prompt
from app.backend.memory.core_memory import load_core_memory
from app.backend.memory.semantic_summary import retrieve_summary
from app.backend.memory.episodic_memory import retrieve_episodes, store_episode, retrieve_personal_facts
from datetime import datetime
from app.backend.chat.agent import agent_executor
from app.backend.chat.schemas import CycloneResponse
from app.backend.scheduler.event_extractor import extract_event
from app.backend.core.queue import reminder_queue
import queue
import re

def clean_message(text):
    return re.sub(r'\{[\s\S]*\}', '', text).strip()

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

chain = prompt | llm.with_structured_output(CycloneResponse)

history = []

def chat(query):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    core_memory = load_core_memory()
    episodes = retrieve_episodes(query)
    summary = retrieve_summary(query)
    personal_facts = retrieve_personal_facts(query)

    try:
        reminder = reminder_queue.get_nowait()
        reminder_context = f"\n--- ACTIVE REMINDER ---\n{reminder}\n"
    except queue.Empty:
        reminder_context = ""

    memory_context = f"""
        --- CURRENT DATE TIME ---
        {now}

        --- CORE MEMORY ---
        {core_memory}
        
        {reminder_context}
        
        --- PERSONAL FACTS ---
        {personal_facts}

        --- PAST EPISODES ---
        {episodes}

        --- SUMMARIES ---
        {summary}
        """
    response = chain.invoke({
        "input": query,
        "history": history,
        "memory_context": memory_context
    })
    print(f"DEBUG tool_call: {response.tool_call}")

    if response.schedule_event: extract_event(response.schedule_event)
    
    if response.tool_call:
        tool_result = agent_executor.invoke({"messages": [("user", response.tool_call.tool_name + " " + str(response.tool_call.parameters))]})
        cleaned = clean_message(tool_result["messages"][-1].content)
    else:
        cleaned = clean_message(response.message)

    store_episode(query, "Thunder")
    store_episode(cleaned, "Cyclone")

    history.append(HumanMessage(content=query))
    history.append(AIMessage(content=cleaned))

    return cleaned