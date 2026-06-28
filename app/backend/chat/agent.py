from langgraph.prebuilt import create_react_agent
from app.backend.core.llm import llm
from app.backend.tools.system_tools import open_application, open_file

tools = [open_application, open_file]

agent_executor = create_react_agent(llm, tools)