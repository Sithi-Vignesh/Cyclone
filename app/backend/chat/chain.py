from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from app.backend.core.llm import llm
from app.backend.prompts.system_prompt import system_prompt
from app.backend.memory.core_memory import load_core_memory
from app.backend.memory.episodic_memory import retrieve_episodes, store_episode
from app.backend.memory.semantic_summary import retrieve_summary

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

chain = prompt | llm

history = []

while True:
    query = input("ME: ")
    if "stop" in query.lower(): break

    core_memory = load_core_memory()
    episodes = retrieve_episodes(query)
    summary = retrieve_summary(query)

    memory_context = f"""
        --- CORE MEMORY ---
        {core_memory}

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
    print("CYCLONE:", response.content)

    store_episode(query, "Thunder")
    store_episode(response.content, "Cyclone")

    history.append(HumanMessage(content=query))
    history.append(AIMessage(content=response.content))