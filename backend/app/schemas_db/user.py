from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, EmailStr
from .common import MongoDBModel

# --- Sub Models (Embedded Documents) ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    nickname: str
    provider: str = "local"
    uid: str = ""

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    job_title: Optional[str] = None


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

class KeywordProgress(BaseModel):
    """
    사용자의 키워드(Keyword)별 학습 이력 (v1.1)
    """
    # 학습 결과 (Star Rating: 1~3)
    # 0: Not started (Learning Started), 1: Bronze, 2: Silver, 3: Gold
    star: int = 0 
    
    # 마지막 학습 시간 (최신 학습에 좀 더 가중치 부여)
    last_reviewed_at: Optional[datetime] = None

# --- Main Collection Model ---

class User(MongoDBModel):
    """
    [Collection]: users
    사용자 정보 및 학습 상태를 저장
    """
    auth: AuthInfo
    profile: UserProfile
    stats: UserStats = Field(default_factory=UserStats)
    
    # [User State] 키워드별 학습 이력
    # Key: Keyword Key (e.g. "Dependency Injection")
    keyword_progress: Dict[str, KeywordProgress] = Field(default_factory=dict)
    
    # [User State] 다음 학습 추천 키워드 (Pre-calculated)
    # 백그라운드에서 계산된 추천 키워드 목록 저장
    recommended_keywords: List[str] = Field(default_factory=list)
    
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
                "keyword_progress": {
                    "FastAPI": {"star": 3, "last_reviewed_at": "2022-01-01T00:00:00.000Z" },
                    "Python": {"star": 2, "last_reviewed_at": "2022-01-01T00:00:00.000Z" }
                },
                "recommended_keywords": ["Pydantic", "AsyncIO"]
            }
        }
