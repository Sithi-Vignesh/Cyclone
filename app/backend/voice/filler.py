from langchain_openai import ChatOpenAI
from openai import RateLimitError
from app.backend.config.settings import GROQ_API_KEYS
from app.backend.core.error_logger import log_error

current_key_index = 0

FALLBACK_LINE = "Give me a sec."

_FILLER_PROMPT_TEMPLATE = (
    "You are Cyclone, a witty personal AI assistant, talking to Thunder. "
    "He just asked: \"{query}\". "
    "Say ONE short, casual sentence that stalls for a second or two while "
    "you're still figuring it out — like you're mid-thought, not done yet. "
    "Never state a specific answer, fact, or result. Never say a task is "
    "done or confirmed. No preamble, no quotes, just the sentence. "
    "Example: query 'play maroon 5' -> 'Lemme pull that up real quick.'\n"
    "Example: query 'what's the weather' -> 'One sec, checking that now.'\n"
    "Example: query 'set a reminder for 5pm' -> 'On it, hang tight.'"
)


def build_filler_llm(api_key):
    global filler_llm
    filler_llm = ChatOpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.1-8b-instant",
    )


build_filler_llm(GROQ_API_KEYS[current_key_index])


def get_filler(query: str) -> str:
    """
    Returns a short filler sentence for the given query using Groq.
    Rotates keys on RateLimitError (429) only, per project rotation policy.
    Never raises — falls back to a pre-written line on total key exhaustion
    or any non-rate-limit failure, consistent with the never-silent-fail policy.
    """
    global current_key_index
    total_keys = len(GROQ_API_KEYS)
    attempts = 0
    prompt = _FILLER_PROMPT_TEMPLATE.format(query=query)

    while attempts < total_keys:
        try:
            response = filler_llm.invoke(prompt)
            return response.content.strip()
        except RateLimitError:
            current_key_index = (current_key_index + 1) % total_keys
            build_filler_llm(GROQ_API_KEYS[current_key_index])
            attempts += 1
        except Exception as e:
            log_error("filler:get_filler", e)
            return FALLBACK_LINE

    log_error(
        "filler:get_filler",
        Exception("All Groq API keys exhausted (rate limited)."),
    )
    return FALLBACK_LINE