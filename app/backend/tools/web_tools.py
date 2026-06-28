import requests
from langchain.tools import tool

@tool
def get_weather(city: str) -> str:
    """Returns current weather for a given city using wttr.in."""
    try:
        response = requests.get(f"https://wttr.in/{city}?format=3", timeout=5)
        return response.text.strip()
    except Exception as e:
        return f"Couldn't fetch weather: {e}"