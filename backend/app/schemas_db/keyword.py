from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from .common import MongoDBModel


class Keyword(MongoDBModel):
    """
    [Collection]: keywords
    기술 키워드와 임베딩 기반 추천에 필요한 메타데이터입니다.
    """
    keyword_key: str
    keyword: Optional[str] = None
    definition: str = ""
    category: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    related_keywords: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
