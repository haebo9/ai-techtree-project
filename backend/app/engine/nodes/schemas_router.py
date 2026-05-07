from typing import Literal, Optional
from pydantic import BaseModel, Field

# ==========================================
# Router Schema
# ==========================================
class KeywordRouterOutput(BaseModel):
    """
    User intent classification for Keyword-based learning flow.
    """
    intent: Literal["KEYWORD_SEARCH", "ANSWER", "RECOMMEND", "CHIT_CHAT"] = Field(
        ..., description="Classified intent: KEYWORD_SEARCH, ANSWER, RECOMMEND, CHIT_CHAT"
    )
    keyword: Optional[str] = Field(
        None, description="Extracted keyword if intent is KEYWORD_SEARCH (e.g., 'BFS', 'Docker')"
    )
    reasoning: str = Field(..., description="Reason for classification")
