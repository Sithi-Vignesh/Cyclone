from langgraph.prebuilt import create_react_agent
from app.backend.core.llm import agent_llm
from app.backend.tools.system_tools import open_application, open_file, get_battery_status
from app.backend.tools.spotify_tools import spotify_play_song
from app.backend.tools.web_tools import get_weather

tools = [open_application, open_file, spotify_play_song, get_weather, get_battery_status]

agent_executor = create_react_agent(agent_llm, tools)