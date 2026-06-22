from langchain_groq import ChatGroq
from app.backend.config.settings import GROQ_API_KEY

llm = ChatGroq(api_key=GROQ_API_KEY, model_name="llama-3.3-70b-versatile")

print(llm.invoke("say hello"))