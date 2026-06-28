import requests
from langchain.tools import tool
from ddgs import DDGS

@tool
def get_weather(city: str) -> str:
    """Returns current weather for a given city using wttr.in."""
    try:
        response = requests.get(f"https://wttr.in/{city}?format=3", timeout=5)
        return response.text.strip()
    except Exception as e:
        return f"Couldn't fetch weather: {e}"
    
@tool
def web_search(query: str) -> str:
    """Searches the web using DuckDuckGo and returns top 3 results."""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
        if not results:
            return "No results found."
        output = ""
        for r in results:
            output += f"**{r['title']}**\n{r['body']}\n{r['href']}\n\n"
        return output.strip()
    except Exception as e:
        return f"Search failed: {e}"