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
    cluster_id: Optional[str] = None # Assigned by clustering algorithm (e.g. "Backend Basics")
    
    # Content
    definition: str # Core explanation of the concept
    summary: Optional[str] = None
    
    # Relationships
    # List of neighbor keyword_keys found via vector similarity
    related_keywords: List[str] = Field(default_factory=list) 
    
    # Resources
    questions: List[str] = Field(default_factory=list) # List of related Question IDs
    resources: List[str] = Field(default_factory=list) # URLs, Docs, etc.
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "keyword_key": "Dependency Injection",
                "embedding": [0.12, 0.88, -0.45],
                "cluster_id": "pattern-01",
                "definition": "A design pattern where dependencies are injected...",
                "summary": "DI decouples components...",
                "related_keywords": ["Inversion of Control", "Spring Bean"],
                "questions": ["q_101", "q_102"],
                "resources": ["https://backend.com/di-guide"]
            }
        }
