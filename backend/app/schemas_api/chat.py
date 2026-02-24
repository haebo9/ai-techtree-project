from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# ==========================================
# Stateless Chat Schemas
# ==========================================
class MessageItem(BaseModel):
    role: str
    content: str
    id: Optional[str] = None      # For Tool Call ID
    name: Optional[str] = None    # For Tool Name

class StatelessChatRequest(BaseModel):
    messages: List[MessageItem]

class StatelessChatResponse(BaseModel):
    response: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)

# ==========================================
# Stateful Chat Schemas
# ==========================================
class StatefulChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier (e.g. Email or UUID)")
    message: str = Field(..., description="User's input message")
    session_id: Optional[str] = Field(None, description="Session ID for persistent memory (not fully used in v1)")
    
    # Optional context overrides
    track: Optional[str] = Field(default="Python")
    topic: Optional[str] = Field(default="General")
    level: Optional[str] = Field(default="Intermediate")

class StatefulChatResponse(BaseModel):
    response: str
    ui_action: Optional[Dict[str, Any]] = None # For v2.0 UI Control (Confetti etc.)
    history: List[str] = Field(default_factory=list) # Optional debug info
