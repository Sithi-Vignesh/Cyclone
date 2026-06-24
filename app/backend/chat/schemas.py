from pydantic import BaseModel
from typing import Literal

class ScheduleEvent(BaseModel):
    title: str
    type: Literal["college", "projects", "personal", "important"]
    date: str
    start_time: str
    end_time: str

class MemoryUpdate(BaseModel):
    content: str
    memory_type: str
    importance: float

class PersonalFact(BaseModel):
    content: str
    topic : str
    action_type: Literal["add", "update", "overwrite"]

class ToolCall(BaseModel):
    tool_name: str
    parameters: dict

class CycloneResponse(BaseModel):
    message: str
    schedule_event: ScheduleEvent | None = None
    memory_update: MemoryUpdate | None = None
    tool_call: ToolCall | None = None
