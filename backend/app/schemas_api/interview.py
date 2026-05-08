from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# ==========================================
# 1. 면접 시작 (Start Interview)
# ==========================================
class StartInterviewRequest(BaseModel):
    user_id: str = Field(..., description="사용자 ID (예: 이메일 또는 UUID)")
    job_title: str = Field(..., description="지원 직무 (예: 서비스 기획자, 마케터, 프론트엔드 개발자 등)")
    experience: str = Field(..., description="경력 (예: 신입, 1-3년차 등)")
    education: str = Field(..., description="학력 (예: 고졸, 전문학사, 학사, 석사, 박사 등)")
    resume: str = Field(..., description="간단한 이력 또는 자기소개 요약")

class StartInterviewResponse(BaseModel):
    session_id: str = Field(..., description="생성된 면접 고유 세션 ID")
    ephemeral_token: str = Field(..., description="OpenAI Realtime WebRTC 접속을 위한 일회용 토큰")
    message: str = Field(..., description="UI 상태 표시용 메시지")

# ==========================================
# 2. 면접 대화 (Chat)
# ==========================================
class ChatRequest(BaseModel):
    message: str = Field(..., description="사용자의 답변 텍스트")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="AI 면접관의 다음 꼬리 질문 또는 리액션")
    # 추후 STT/TTS를 위한 음성 데이터 URL이나 추가 메타데이터가 들어갈 수 있습니다.

# ==========================================
# 3. 면접 종료 및 평가 (End & Evaluate)
# ==========================================
class TranscriptItem(BaseModel):
    role: str = Field(..., description="발화자 (ai 또는 user)")
    text: str = Field(..., description="발화 내용")

class EndInterviewRequest(BaseModel):
    transcripts: List[TranscriptItem] = Field(default=[], description="전체 대화 내역")

class EndInterviewResponse(BaseModel):
    session_id: str
    score: int
    strengths: List[str]
    weaknesses: List[str]
    job_recommendations: List[Dict[str, str]]
