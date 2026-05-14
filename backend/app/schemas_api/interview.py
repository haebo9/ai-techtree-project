from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict, Any, Optional

# ==========================================
# 1. 면접 시작 (Start Interview)
# ==========================================
class StartInterviewRequest(BaseModel):
    user_id: str = Field(..., description="사용자 ID (예: 이메일 또는 UUID)")
    report_email: EmailStr = Field(..., description="비동기 리포트를 받을 이메일 주소")
    job_title: str = Field(..., description="지원 직무 (예: 서비스 기획자, 마케터, 프론트엔드 개발자 등)")
    experience: str = Field(..., description="경력 (예: 신입, 1-3년차 등)")
    education: str = Field(..., description="학력 (예: 고졸, 전문학사, 학사, 석사, 박사 등)")
    resume: str = Field(..., description="간단한 이력 또는 자기소개 요약")
    job_description: Optional[str] = Field(default="", description="사용자가 직접 입력한 채용 공고 텍스트")
    job_image: Optional[str] = Field(default=None, description="채용 공고 이미지의 Base64 인코딩 문자열")
    interview_mode: str = Field(default="long", description="면접 길이 모드 (short: 7분 내외, long: 20분 내외)")

class StartInterviewResponse(BaseModel):
    session_id: str = Field(..., description="생성된 면접 고유 세션 ID")
    ephemeral_token: str = Field(..., description="OpenAI Realtime WebRTC 접속을 위한 일회용 토큰")
    message: str = Field(..., description="UI 상태 표시용 메시지")
    job_posting_analysis: Dict[str, Any] = Field(default_factory=dict, description="지원 공고 텍스트/이미지 분석 상태 및 요약")
    interview_mode: Optional[str] = Field(default=None, description="정규화된 면접 모드")
    prompt_variant: Optional[str] = Field(default=None, description="Realtime에 주입된 프롬프트 variant")
    guideline_selection: Dict[str, Any] = Field(default_factory=dict, description="주입된 reflection/policy 지침 id와 텍스트 요약")

# ==========================================
# 2. 면접 종료 및 평가 (End & Evaluate)
# ==========================================
class TranscriptItem(BaseModel):
    role: str = Field(..., description="발화자 (ai 또는 user)")
    text: str = Field(..., description="발화 내용")

class EndInterviewRequest(BaseModel):
    transcripts: List[TranscriptItem] = Field(default=[], description="전체 대화 내역")
    saved_jobs: List[Dict[str, Any]] = Field(default=[], description="면접 중 수집된 실제 채용 공고")
    tool_traces: List[Dict[str, Any]] = Field(default=[], description="면접 중 외부 도구 호출 상태와 필터링 사유")
    interview_date: Optional[str] = Field(default=None, description="면접 종료 시각 표시 문자열")
    interview_duration: Optional[str] = Field(default=None, description="면접 소요 시간 표시 문자열")

class EndInterviewResponse(BaseModel):
    session_id: str
    status: str = Field(default="queued", description="리포트 생성 큐잉 상태")
    message: str = Field(default="면접이 종료되었습니다. 리포트는 이메일로 전송됩니다.")
