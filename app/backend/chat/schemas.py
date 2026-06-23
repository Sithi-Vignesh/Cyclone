from pydantic import BaseModel

class ScheduleEvent(BaseModel):
    title: str
    datetime: str

class MemoryUpdate(BaseModel):
    content: str
    memory_type: str
    importance: float

class ToolCall(BaseModel):
    tool_name: str
    parameters: dict

class CycloneResponse(BaseModel):
    message: str
    schedule_event: ScheduleEvent | None = None
    memory_update: MemoryUpdate | None = None
    tool_call: ToolCall | None = None
