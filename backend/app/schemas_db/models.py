from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class UserProfile(BaseModel):
    """사용자의 기본 프로필 정보"""
    user_id: str
    job_title: str
    field: str
    experience: str
    major: str

class InterviewSession(BaseModel):
    """하나의 면접 세션을 기록하는 스키마"""
    session_id: str
    user_id: str
    messages: List[Dict[str, Any]] = [] # 대화 기록 (User, AI)
    status: str = "IN_PROGRESS"         # IN_PROGRESS, EVALUATING, COMPLETED
    created_at: datetime = Field(default_factory=datetime.utcnow)

class EvaluationReport(BaseModel):
    """면접 종료 후 생성되는 종합 리포트 스키마"""
    session_id: str
    user_id: str
    score: int
    strengths: List[str]
    weaknesses: List[str]
    job_recommendations: List[Dict[str, str]]
    communication_feedback: Dict[str, Any] = Field(default_factory=dict)
    self_intro_feedback: Dict[str, Any] = Field(default_factory=dict)
    role_fit: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
