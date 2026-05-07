from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# ==========================================
# 1. 면접 시작 (Start Interview)
# ==========================================
class StartInterviewRequest(BaseModel):
    user_id: str = Field(..., description="사용자 ID (예: 이메일 또는 UUID)")
    job_title: str = Field(..., description="희망 상세 직무 (예: React 프론트엔드 개발자)")
    field: str = Field(..., description="희망 분야 (예: frontend, backend)")
    experience: str = Field(..., description="경력 (예: newcomer, 1-3, 3-5, 5+)")
    major: str = Field(..., description="전공 여부 (예: cs, non-cs)")

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
class EndInterviewResponse(BaseModel):
    session_id: str
    score: int
    strengths: List[str]
    weaknesses: List[str]
    job_recommendations: List[Dict[str, str]]
