from langchain_openai import ChatOpenAI
from openai import RateLimitError
from app.backend.config.settings import OPENROUTER_API_KEYS

current_key_index = 0

def build_llms(api_key):
    global llm, agent_llm, summarization_llm
    llm = ChatOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model="nvidia/nemotron-3-nano-30b-a3b:free",
    )
    agent_llm = ChatOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model="openai/gpt-oss-120b:free",
    )
    summarization_llm = ChatOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        model="nvidia/nemotron-nano-9b-v2:free",
    )

build_llms(OPENROUTER_API_KEYS[current_key_index])

def invoke_with_rotation(llm_name: str, *args, **kwargs):
    global current_key_index
    total_keys = len(OPENROUTER_API_KEYS)
    attempts = 0
    while attempts < total_keys:
        try:
            obj = globals()[llm_name]
            return obj.invoke(*args, **kwargs)
        except RateLimitError:
            current_key_index = (current_key_index + 1) % total_keys
            build_llms(OPENROUTER_API_KEYS[current_key_index])
            attempts += 1
    raise Exception("All API keys exhausted. Try again tomorrow.")