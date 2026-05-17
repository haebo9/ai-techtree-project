import json
import re
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field
from app.engine.graphs.state import InterviewState
from app.core.llm import get_llm
from langchain_core.messages import SystemMessage

from app.engine.prompts.evaluator import EVALUATOR_SYSTEM_PROMPT_TEMPLATE

class QnAReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(description="면접관의 질문")
    answer: str = Field(description="지원자의 답변 요약")
    feedback: str = Field(description="해당 답변에 대한 AI의 상세 피드백 (긍정적 요소 및 개선점)")

class CommunicationFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(default="", description="지원자의 말투와 답변 습관에 대한 종합 요약")
    strengths: List[str] = Field(default_factory=list, description="말하기 방식에서 드러난 장점")
    habits_to_improve: List[str] = Field(default_factory=list, description="개선하면 좋은 말투/답변 습관")
    action_items: List[str] = Field(default_factory=list, description="다음 면접에서 바로 적용할 수 있는 개선 행동")

class SelfIntroFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_summary: str = Field(default="", description="면접 중 사용자가 실제로 말한 자기소개 또는 자기소개성 답변 요약")
    issues: List[str] = Field(default_factory=list, description="실제 자기소개 답변에서 보완할 점")
    improvement_direction: str = Field(default="", description="이력서와 직무를 반영한 자기소개 개선 방향")
    improved_script: str = Field(default="", description="45-60초 분량의 개선된 자기소개 전체 멘트")
    evidence_note: str = Field(default="", description="실제 자기소개 답변 근거가 충분했는지에 대한 짧은 설명")

class RoleFit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(default=0, ge=0, le=100, description="이력서와 목표 직무의 적합도 퍼센트 (0-100)")
    rationale: str = Field(default="", description="적합도 퍼센트 산정 근거")
    matched_keywords: List[str] = Field(default_factory=list, description="이력서/면접에서 확인된 직무 관련 강점 키워드")
    gaps: List[str] = Field(default_factory=list, description="직무 적합도를 높이기 위해 보완할 부분")

class EvaluationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(description="면접 종합 점수 (0-100)")
    strengths: List[str] = Field(description="지원자의 주요 강점 목록")
    weaknesses: List[str] = Field(description="보완이 필요한 점 목록")
    qa_review: List[QnAReview] = Field(description="주요 질의응답 내역 및 피드백 (최대 3개)")
    communication_feedback: CommunicationFeedback = Field(description="말투와 답변 습관 피드백")
    self_intro_feedback: SelfIntroFeedback = Field(description="이력서 기반 자기소개 피드백")
    role_fit: RoleFit = Field(description="이력서와 목표 직무의 적합도 평가")

def evaluator_node(state: InterviewState):
    """
    평가자 AI 노드:
    전체 대화 내역을 바탕으로 종합 리포트를 생성합니다.
    """
    llm = get_llm(temperature=0.2) # 평가의 일관성을 위해 낮은 온도로 설정
    structured_llm = llm.with_structured_output(EvaluationSchema)
    
    user_id = state.get('user_id', '지원자')
    job_title = state.get('job_title', '정보 없음')
    job_description = state.get('job_description', '맞춤형 채용 공고 정보 없음')
    resume = state.get('resume', '이력서 정보 없음')
    interview_mode_label = state.get('interview_mode_label', '면접 모드 정보 없음')
    tool_traces = state.get('tool_traces', [])
    
    system_prompt = EVALUATOR_SYSTEM_PROMPT_TEMPLATE.format(
        user_id=user_id,
        job_title=job_title,
        interview_mode_label=interview_mode_label,
        resume=resume,
        job_description=job_description,
        tool_traces=tool_traces,
    )

    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    result = structured_llm.invoke(messages)
    
    result_dict = result.model_dump()
    
    return {"evaluation_result": result_dict, "status": "COMPLETED"}
