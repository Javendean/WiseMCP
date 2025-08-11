from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel, Column, JSON

# --- API Models ---

class ToolParameterProperty(BaseModel):
    type: str
    description: str

class ToolParameters(BaseModel):
    type: str = "object"
    properties: Dict[str, ToolParameterProperty]
    required: List[str]

class Tool(BaseModel):
    name: str
    description: str
    parameters: ToolParameters

class ToolExecutionRequest(BaseModel):
    name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

class ToolExecutionResponse(BaseModel):
    result: str

# --- Database Model ---

class ToolCallHistory(SQLModel, table=True):
    """
    Represents the schema for the persistent conversational memory.
    Each record is a single tool call and its result.
    """
    id: Optional[int] = SQLField(default=None, primary_key=True)
    conversation_id: str
    timestamp: datetime = SQLField(default_factory=datetime.utcnow)
    tool_name: str
    request_params: Dict[str, Any] = SQLField(sa_column=Column(JSON))
    response_content: str
