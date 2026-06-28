from langchain_openai import ChatOpenAI
from app.backend.config.settings import OPENROUTER_API_KEY

llm = ChatOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    model="nvidia/nemotron-3-nano-30b-a3b:free",
)

agent_llm = ChatOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    model="openai/gpt-oss-120b:free",
)

summarization_llm = ChatOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    model="nvidia/nemotron-nano-9b-v2:free",
)