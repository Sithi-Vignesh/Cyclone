from langgraph.prebuilt import create_react_agent
from app.backend.core.llm import llm
from app.backend.tools.system_tools import open_application, open_file
from app.backend.tools.spotify_tools import spotify_play_song
from app.backend.core.llm import agent_llm

tools = [open_application, open_file,spotify_play_song]

agent_executor = create_react_agent(agent_llm, tools)