from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from app.backend.core.llm import llm
from app.backend.prompts.system_prompt import system_prompt

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
    
    response = chain.invoke({"input": query, "history": history})
    print("CYCLONE:", response.content)
    
    history.append(HumanMessage(content=query))
    history.append(AIMessage(content=response.content))