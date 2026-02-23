from typing import TypedDict, List, Optional
from typing_extensions import Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# ==========================================
# 1. State Definition
# ==========================================
# 키워드 관련 상태 저장 클래스
class KeywordState(TypedDict, total=False):
    """
    State for the Keyword-Driven Learning Flow.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User Context
    user_id: str
    user_db_id: str
    
    # Current Focus
    keyword: str             # The active keyword
    keyword_data: dict       # Extracted/Generated content (def, summary)
    level: int               # The level of the keyword
    
    # Quiz Context
    current_question: Optional[dict]
    evaluation_result: Optional[dict]
    
    # Navigation
    next_recommendations: List[str]
    user_intent: str         # From Router
    pass_fail: str           # From Evaluate Quiz
    
    # Context Flags
    quiz_in_progress: bool = False # 퀴즈 진행 중 여부
