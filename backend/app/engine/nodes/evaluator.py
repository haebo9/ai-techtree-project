from typing import List
from pydantic import BaseModel, Field
from app.engine.graphs.state import InterviewState
from app.core.llm import get_llm
from langchain_core.messages import SystemMessage

class JobRecommendation(BaseModel):
    company: str = Field(description="추천 회사명")
    title: str = Field(description="추천 직무명")
    url: str = Field(description="해당 채용 공고의 실제 URL (있을 경우에만 작성)", default="")

    class Config:
        extra = "forbid"

class QnAReview(BaseModel):
    question: str = Field(description="면접관의 질문")
    answer: str = Field(description="지원자의 답변 요약")
    feedback: str = Field(description="해당 답변에 대한 AI의 상세 피드백 (긍정적 요소 및 개선점)")

    class Config:
        extra = "forbid"

class EvaluationSchema(BaseModel):
    score: int = Field(description="면접 종합 점수 (0-100)")
    strengths: List[str] = Field(description="지원자의 주요 강점 목록")
    weaknesses: List[str] = Field(description="보완이 필요한 점 목록")
    qa_review: List[QnAReview] = Field(description="주요 질의응답 내역 및 피드백 (최대 3개)")
    job_recommendations: List[JobRecommendation] = Field(description="추천 채용 공고 목록")

    class Config:
        extra = "forbid"

def evaluator_node(state: InterviewState):
    """
    평가자 AI 노드:
    전체 대화 내역을 바탕으로 종합 리포트를 생성합니다.
    """
    llm = get_llm(temperature=0.2) # 평가의 일관성을 위해 낮은 온도로 설정
    structured_llm = llm.with_structured_output(EvaluationSchema)
    
    user_id = state.get('user_id', '지원자')
    job_title = state.get('job_title', '정보 없음')
    
    system_prompt = f"""
    당신은 전문 채용 평가관입니다. 지원자({user_id})의 면접 대화 전체를 분석하여 
    객관적이고 전문적인 피드백을 제공하세요.
    - 지원 직무: {job_title}
    - 강점과 약점은 실무적인 관점에서 구체적으로 작성하세요.
    - 면접 중 가장 핵심이 되었던 주요 질문과 답변을 3개 이내로 선정하고, 해당 답변이 어땠는지(현업 트렌드, 논리성 등) 구체적인 코멘트를 'qa_review' 항목에 작성하세요.
    - 'job_recommendations' 항목은 항상 빈 배열([])로 반환하세요. 공고 정보는 시스템이 별도로 주입합니다.
    
    [중요] 만약 면접 대화가 너무 짧거나(인사말만 있거나), 답변 내용이 부족하여 평가가 불가능하다면, 
    점수를 0점으로 주고, 강점/약점에 "대화 내용이 부족하여 평가할 수 없습니다."라고 명시하세요.
    """
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    result = structured_llm.invoke(messages)
    
    result_dict = result.dict()
    
    # LLM 환각 방지를 위해, 프론트엔드에서 수집한 실제 검색 결과(saved_jobs)를 강제로 주입
    saved_jobs = state.get("saved_jobs", [])
    if saved_jobs:
        # Pydantic 스키마에 맞게 필터링
        filtered_jobs = []
        for job in saved_jobs:
            filtered_jobs.append({
                "company": job.get("company", "회사명 미상"),
                "title": job.get("title", "공고명 미상"),
                "url": job.get("url", "")
            })
        result_dict["job_recommendations"] = filtered_jobs
    else:
        result_dict["job_recommendations"] = []
    
    return {"evaluation_result": result_dict, "status": "COMPLETED"}
