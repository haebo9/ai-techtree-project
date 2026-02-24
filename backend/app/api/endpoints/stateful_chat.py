from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.engine.graphs.interview_graph import app as interview_graph
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

router = APIRouter()

# --- Request/Response Schemas ---

class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier (e.g. Email or UUID)")
    message: str = Field(..., description="User's input message")
    session_id: Optional[str] = Field(None, description="Session ID for persistent memory (not fully used in stateless v1)")
    
    # Optional context overrides
    track: Optional[str] = "Python"
    topic: Optional[str] = "General"
    level: Optional[str] = "Intermediate"

class ChatResponse(BaseModel):
    response: str
    ui_action: Optional[Dict[str, Any]] = None # For v2.0 UI Control (Confetti etc.)
    history: List[str] = [] # Optional debug info

# --- Endpoints ---

@router.post("/message", response_model=ChatResponse)
async def chat_message(req: ChatRequest):
    """
    [v2] Stateful Interview Chat Endpoint
    Executes the LangGraph Agent.
    """
    try:
        # 1. State Configuration
        # In a real production scenario with checkpointer, we would load state by thread_id.
        # For this prototype, we rebuild partial state from request or assume client manages history.
        # However, to be truly stateful without client history management, we need a DB-backed checkpointer.
        # Since v1.1 goal is 'Stateful Agent', we ideally use LangGraph Checkpointer.
        # BUT for now, we will assume a "stateless API, stateful Logic" approach where user sends just the message,
        # and we might load minimal context from DB in 'load_state' node.
        # To keep conversation flow, we simply pass the single new message.
        # Real-world fix: Persist 'messages' in DB or Redis. 
        
        inputs = {
            "user_id": req.user_id,
            "messages": [HumanMessage(content=req.message)],
            "track": req.track,
            "topic": req.topic,
            "level": req.level
        }
        
        # 2. Run Graph
        # We use invoke to process the turn.
        # The graph will load DB state (stars, etc) in 'load_state' node.
        # But 'messages' history? If we don't pass past messages, the agent has no memory of previous turns invokation.
        # This is the limitation of NO-Checkpointer.
        # For v1.1, let's assume the Client (frontend) or User sends just current message, 
        # and we rely on 'current_question' being loaded from DB? 
        # Actually our graph expects 'messages' to be the history.
        
        # Temporary Solution for v1.1 API:
        # We just run with the current message. 
        # The 'router' might struggle without context if user says "Next".
        # But 'load_state' logic typically should load the 'Active Session' from DB.
        
        config = {"configurable": {"thread_id": req.user_id}} # If we had checkpointer
        
        # Execute
        result = await interview_graph.ainvoke(inputs)
        
        # 3. Parse Result
        messages = result.get("messages", [])
        last_msg = messages[-1] if messages else AIMessage(content="No response.")
        
        response_text = last_msg.content if isinstance(last_msg, BaseMessage) else str(last_msg)
        
        return ChatResponse(
            response=response_text,
            ui_action=None, # Future v2
            history=[m.content for m in messages]
        )

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
