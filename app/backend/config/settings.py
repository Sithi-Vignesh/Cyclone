from dotenv import load_dotenv
import os

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEYS = [
    os.getenv("OPENROUTER_API_KEY1"),
    os.getenv("OPENROUTER_API_KEY2"),
    os.getenv("OPENROUTER_API_KEY3"),
]