from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field

from .common import MongoDBModel


class TrendCategory(str, Enum):
    AI = "ai"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATA = "data"
    DEVOPS = "devops"
    CAREER = "career"
    GENERAL = "general"


class Trend(MongoDBModel):
    """
    [Collection]: trends
    기술 트렌드/검색 결과 저장용 레거시 스키마입니다.
    """
    title: str
    category: TrendCategory = TrendCategory.GENERAL
    summary: str = ""
    url: Optional[str] = None
    source: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
