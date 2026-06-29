from langgraph.prebuilt import create_react_agent
from app.backend.core.llm import agent_llm
from datetime import datetime
from app.backend.tools.system_tools import open_application, open_file, get_battery_status, read_clipboard, get_active_window, get_all_windows
from app.backend.tools.memory_tools import delete_all_memory, get_upcoming_events
from app.backend.tools.spotify_tools import spotify_play_song
from app.backend.tools.web_tools import get_weather, web_search

tools = [
    open_application,
    open_file, 
    spotify_play_song, 
    get_weather, 
    get_battery_status, 
    web_search, 
    read_clipboard, 
    get_active_window, 
    get_all_windows, 
    delete_all_memory, 
    get_upcoming_events,
    ]

agent_executor = create_react_agent(
    agent_llm, 
    tools,
    prompt=f"""You are a helpful research assistant. Today's date is {datetime.now().strftime('%Y-%m-%d')}. Always use the current year when searching for recent information.
    Keep your final response concise and conversational — no tables, no markdown headers, no bullet lists unless explicitly asked."""
)