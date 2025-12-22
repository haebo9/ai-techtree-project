from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, EmailStr
from .common import MongoDBModel

# --- Sub Models (Embedded Documents) ---

class AuthInfo(BaseModel):
    email: EmailStr
    provider: str  # e.g., 'kakao', 'google'
    uid: str       # Provider's unique user ID

class UserProfile(BaseModel):
    nickname: str
    avatar_url: Optional[str] = None
    job_title: Optional[str] = None

class UserStats(BaseModel):
    total_stars: int = 0
    completed_tracks: List[str] = []

class SkillProgress(BaseModel):
    """
    사용자의 기술별 진행 상황
    """
    order: int
    level: int = 0  # 0: Locked, 1: Basic, 2: Adv, 3: Master
    stars: int = 0
    last_tested_at: Optional[datetime] = None

# --- Main Collection Model ---

class User(MongoDBModel):
    """
    [Collection]: users
    사용자 정보 및 학습 상태(Skill Tree)를 저장
    """
    auth: AuthInfo
    profile: UserProfile
    stats: UserStats = Field(default_factory=UserStats)
    
    # 핵심 구조: 빠른 조회를 위해 Skill Tree를 내장(Embedding)
    # Key: skill_slug (e.g., 'python')
    skill_tree: Dict[str, SkillProgress] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "auth": {
                    "email": "user@example.com",
                    "provider": "kakao",
                    "uid": "12345"
                },
                "profile": {
                    "nickname": "AI_Master"
                },
                "skill_tree": {
                    "python": {"order": 1, "level": 2, "stars": 2}
                }
            }
        }
