from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEYS = [
    os.getenv("GROQ_API_KEY1"),
    os.getenv("GROQ_API_KEY2"),
    os.getenv("GROQ_API_KEY3"),
    # GROQ_API_KEY4 intentionally skipped — not added yet
    os.getenv("GROQ_API_KEY5"),
    os.getenv("GROQ_API_KEY6"),
]

OPENROUTER_API_KEYS = [
    os.getenv("OPENROUTER_API_KEY1"),
    os.getenv("OPENROUTER_API_KEY2"),
    os.getenv("OPENROUTER_API_KEY3"),
    os.getenv("OPENROUTER_API_KEY4"),
    os.getenv("OPENROUTER_API_KEY5"),
    os.getenv("OPENROUTER_API_KEY6"),
]