from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from app.backend.core.llm import llm
from app.backend.prompts.system_prompt import system_prompt
from app.backend.memory.core_memory import load_core_memory
from app.backend.memory.semantic_summary import retrieve_summary
from app.backend.memory.episodic_memory import retrieve_episodes, store_episode, retrieve_personal_facts
from datetime import datetime
from app.backend.chat.schemas import CycloneResponse
from app.backend.scheduler.event_extractor import extract_event
from app.backend.core.queue import reminder_queue
import queue

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

    memory_context = f"""
        --- CURRENT DATE TIME ---
        {now}

        --- CORE MEMORY ---
        {core_memory}

        --- PERSONAL FACTS ---
        {personal_facts}

        --- PAST EPISODES ---
        {episodes}

        --- SUMMARIES ---
        {summary}
        """

    try:
        reminder = reminder_queue.get_nowait()
        memory_context += f"\n\n[REMINDER] {reminder}"
    except queue.Empty:
        pass

    response = chain.invoke({
        "input": query,
        "history": history,
        "memory_context": memory_context
    })

    if response.schedule_event: extract_event(response.schedule_event)

    store_episode(query, "Thunder")
    store_episode(response.message, "Cyclone")

    history.append(HumanMessage(content=query))
    history.append(AIMessage(content=response.message))

    return response.message