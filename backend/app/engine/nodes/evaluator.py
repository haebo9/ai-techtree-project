import json
import re
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field
from app.engine.graphs.state import InterviewState
from app.core.llm import get_llm
from langchain_core.messages import SystemMessage

class JobRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str = Field(description="추천 회사명")
    title: str = Field(description="추천 직무명")
    url: str = Field(description="해당 채용 공고의 실제 URL (있을 경우에만 작성)", default="")

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

    score: int = Field(default=0, ge=0, le=100, description="이력서와 목표 직무의 적합도 점수 (0-100)")
    rationale: str = Field(default="", description="적합도 점수 산정 근거")
    matched_keywords: List[str] = Field(default_factory=list, description="이력서/면접에서 확인된 직무 관련 강점 키워드")
    gaps: List[str] = Field(default_factory=list, description="직무 적합도를 높이기 위해 보완할 부분")

class EvaluationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(description="면접 종합 점수 (0-100)")
    strengths: List[str] = Field(description="지원자의 주요 강점 목록")
    weaknesses: List[str] = Field(description="보완이 필요한 점 목록")
    qa_review: List[QnAReview] = Field(description="주요 질의응답 내역 및 피드백 (최대 3개)")
    job_recommendations: List[JobRecommendation] = Field(description="추천 채용 공고 목록")
    communication_feedback: CommunicationFeedback = Field(description="말투와 답변 습관 피드백")
    self_intro_feedback: SelfIntroFeedback = Field(description="이력서 기반 자기소개 피드백")
    role_fit: RoleFit = Field(description="이력서와 목표 직무의 적합도 평가")

def _normalize_saved_jobs(raw_jobs: Any) -> List[Dict[str, str]]:
    """
    Convert search results from Tavily/tool calls into the report schema.
    Handles the current structured list and older string summaries defensively.
    """
    if not raw_jobs:
        return []

    if isinstance(raw_jobs, str):
        try:
            raw_jobs = json.loads(raw_jobs)
        except json.JSONDecodeError:
            jobs = []
            for line in raw_jobs.splitlines():
                match = re.search(r"-\s*(?P<title>.*?)(?:\s*\(링크:\s*(?P<url>.*?)\))?$", line.strip())
                if not match:
                    continue
                title = match.group("title").strip()
                if title:
                    jobs.append({
                        "company": "회사명 미상",
                        "title": title,
                        "url": (match.group("url") or "").strip(),
                        "content": "",
                    })
            return jobs

    if isinstance(raw_jobs, dict):
        raw_jobs = [raw_jobs]

    if not isinstance(raw_jobs, list):
        return []

    normalized = []
    for job in raw_jobs:
        if not isinstance(job, dict):
            continue
        normalized.append({
            "company": str(job.get("company") or "회사명 미상"),
            "title": str(job.get("title") or "공고명 미상"),
            "url": str(job.get("url") or ""),
            "content": str(job.get("content") or ""),
        })
    return normalized

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
    
    system_prompt = f"""
    당신은 전문 채용 평가관입니다. 지원자({user_id})의 면접 대화 전체를 분석하여 
    객관적이고 전문적인 피드백을 제공하세요.
    - 지원 직무: {job_title}
    - 면접 모드: {interview_mode_label}
    - 지원자 이력서/프로필: {resume}
    - 맞춤형 채용 공고 요건 (참고용): {job_description}
    - 강점과 약점은 위 직무 및 공고 요건(있을 경우)의 실무적인 관점에서 구체적으로 작성하세요.
    - 면접 중 가장 핵심이 되었던 주요 질문과 답변을 3개 이내로 선정하고, 해당 답변이 어땠는지(현업 트렌드, 논리성 등) 구체적인 코멘트를 'qa_review' 항목에 작성하세요.
    - 'communication_feedback'은 대화 기록에서 확인되는 말투, 답변 길이, 구조화 방식, 불필요한 반복/추임새, 마무리 습관을 평가하세요. 성격이나 인성을 단정하지 말고 면접 전달 방식만 다루세요.
    - 'self_intro_feedback'은 사용자가 실제로 말한 자기소개 또는 자기소개성 답변을 우선 참고하세요. 이력서의 핵심 경험과 지원 직무를 연결하여 45-60초 분량의 개선된 자기소개 전체 멘트를 'improved_script'에 작성하세요.
    - 실제 자기소개 답변이 없거나 너무 짧으면, 'evidence_note'에 "실제 자기소개 답변 근거가 부족하여 이력서 기반으로 작성했습니다."라고 명시하고 이력서 기반 추천 멘트를 작성하세요.
    - 'role_fit'은 최종 면접 점수와 별개입니다. 이력서, 지원 직무, 공고 요건, 면접 답변을 종합해 0-100점으로 산정하고, 강점 키워드와 보완 갭을 구체적으로 작성하세요.
    - 'job_recommendations' 항목은 항상 빈 배열([])로 반환하세요. 공고 정보는 시스템이 별도로 주입합니다.
    
    [중요] 만약 면접 대화가 너무 짧거나(인사말만 있거나), 답변 내용이 부족하여 평가가 불가능하다면, 
    점수를 0점으로 주고, 강점/약점에 "대화 내용이 부족하여 평가할 수 없습니다."라고 명시하세요.
    이 경우에도 새 피드백 항목들은 빈 값으로 두지 말고, 근거 부족과 다음 연습 방향을 짧게 작성하세요.
    """
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    result = structured_llm.invoke(messages)
    
    result_dict = result.model_dump()
    
    # LLM 환각 방지를 위해, 프론트엔드에서 수집한 실제 검색 결과(saved_jobs)를 강제로 주입
    saved_jobs = _normalize_saved_jobs(state.get("saved_jobs", []))
    
    filtered_jobs = saved_jobs[:3]
                
    result_dict["job_recommendations"] = filtered_jobs
    
    return {"evaluation_result": result_dict, "status": "COMPLETED"}
