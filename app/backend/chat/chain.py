from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from app.backend.core.llm import invoke_with_rotation, build_llms
import app.backend.core.llm as llm_module
from app.backend.prompts.system_prompt import system_prompt
from app.backend.memory.core_memory import load_core_memory
from app.backend.memory.semantic_summary import retrieve_summary
from app.backend.memory.episodic_memory import retrieve_episodes, store_episode, retrieve_personal_facts
from datetime import datetime
from app.backend.chat.schemas import CycloneResponse
from app.backend.scheduler.event_extractor import extract_event
from app.backend.core.queue import reminder_queue
from app.backend.tools.system_tools import open_application, open_file, get_battery_status, read_clipboard, get_active_window, get_all_windows
from app.backend.tools.memory_tools import delete_all_memory, get_upcoming_events
from app.backend.tools.spotify_tools import spotify_play_song
from app.backend.tools.web_tools import get_weather, web_search
from app.backend.chat.agent import agent_executor
from openai import RateLimitError
from app.backend.config.settings import OPENROUTER_API_KEYS
import queue
import re

tool_registry = {
    "open_application": open_application,
    "open_file": open_file,
    "spotify_play_song": spotify_play_song,
    "get_battery_status": get_battery_status,
    "get_weather": get_weather,
    "web_search": web_search,
    "read_clipboard": read_clipboard,
    "get_active_window": get_active_window,
    "get_all_windows": get_all_windows,
    "get_upcoming_events":get_upcoming_events,
    "delete_all_memory": delete_all_memory,
}

def clean_message(text):
    return re.sub(r'\{[\s\S]*\}', '', text).strip()

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

def get_chain():
    return prompt | llm_module.llm.with_structured_output(CycloneResponse)

history = []

def invoke_chain(payload):
    total_keys = len(OPENROUTER_API_KEYS)
    attempts = 0
    while attempts < total_keys:
        try:
            return get_chain().invoke(payload)
        except RateLimitError:
            llm_module.current_key_index = (llm_module.current_key_index + 1) % total_keys
            build_llms(OPENROUTER_API_KEYS[llm_module.current_key_index])
            attempts += 1
    raise Exception("All API keys exhausted. Try again tomorrow.")

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

    response = invoke_chain({
        "input": query,
        "history": history,
        "memory_context": memory_context
    })
    print(f"DEBUG tool_calls: {response.tool_calls}, use_agent: {response.use_agent}")

    if response.schedule_event: extract_event(response.schedule_event)

    if response.use_agent:
        agent_result = agent_executor.invoke({"messages": [HumanMessage(content=query)]})
        cleaned = clean_message(agent_result["messages"][-1].content)
    elif response.tool_calls:
        tool_results = []
        for tool_call in response.tool_calls:
            tool_result = tool_registry[tool_call.tool_name].invoke(tool_call.parameters)
            tool_results.append(f"[{tool_call.tool_name}]: {tool_result}")
        combined = "\n\n".join(tool_results)
        summary_response = invoke_with_rotation(
            "summarization_llm",
            f"The user asked: {query}\n\nTool results:\n{combined}\n\nAnswer the user's question using these results. Be concise and natural."
        )
        cleaned = clean_message(summary_response.content)
    else:
        cleaned = clean_message(response.message)

    store_episode(query, "Thunder")
    store_episode(cleaned, "Cyclone")

    history.append(HumanMessage(content=query))
    history.append(AIMessage(content=cleaned))

    return cleaned