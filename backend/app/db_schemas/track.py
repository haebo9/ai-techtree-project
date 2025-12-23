from typing import List, Optional, Literal
from pydantic import BaseModel
from .common import MongoDBModel

class TrackNode(BaseModel):
    """
    트랙 내의 개별 학습 노드 (스킬)
    """
    skill_slug: str
    required_level: int = 1
    
    # 의존성 관리
    dependencies: List[str] = [] # 선행 스킬 slug 목록
    
    # 선택적 분기 (OR 조건) 지원
    group_id: Optional[str] = None # 같은 그룹끼리는 선택 관계
    dependency_logic: Literal["AND", "OR"] = "AND"

class Track(MongoDBModel):
    """
    [Collection]: tracks
    직무별 로드맵 구조 정의 (Read-Only)
    """
    slug: str               # URL path (e.g., 'backend-developer')
    title: str
    description: str
    
    nodes: List[TrackNode]
    
    class Config:
        json_schema_extra = {
            "example": {
                "slug": "backend-developer",
                "title": "Backend Master",
                "nodes": [
                    {"skill_slug": "python", "required_level": 3},
                    {"skill_slug": "fastapi", "dependencies": ["python"]}
                ]
            }
        }
