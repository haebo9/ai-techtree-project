from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from .common import MongoDBModel

class Keyword(MongoDBModel):
    """
    [Collection]: keywords
    The fundamental unit of the knowledge graph (v1.1).
    Replaces the static Hierarchy with a semantic network.
    """
    keyword_key: str  # Unique Primary Key (e.g. "Dependency Injection")
    
    # Semantic Search
    embedding: List[float] = Field(default_factory=list) # Vector embedding for semantic search
    
    # Grouping (Dynamic)
    # cluster_id REMOVED: Will be handled dynamically via vector clustering in v1.2
    
    # Content
    definition: str # Core explanation of the concept
    summary: Optional[str] = None

    # Date
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "keyword_key": "Dependency Injection",
                "embedding": [0.12, 0.88, -0.45],

                "definition": "A design pattern where dependencies are injected...",
                "summary": "DI decouples components...",

                "updated_at": "2022-01-01T00:00:00.000Z"

            }
        }
