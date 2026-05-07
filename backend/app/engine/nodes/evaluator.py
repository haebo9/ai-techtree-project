from typing import List
from pydantic import BaseModel, Field
from app.engine.graphs.state import InterviewState
from app.core.llm import get_llm
from langchain_core.messages import SystemMessage

class JobRecommendation(BaseModel):
    company: str = Field(description="추천 회사명")
    title: str = Field(description="추천 직무명")

    class Config:
        extra = "forbid"

class EvaluationSchema(BaseModel):
    score: int = Field(description="면접 종합 점수 (0-100)")
    strengths: List[str] = Field(description="지원자의 주요 강점 목록")
    weaknesses: List[str] = Field(description="보완이 필요한 점 목록")
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
    당신은 전문 채용 평가관입니다. 지원자({user_id})의 면접 답변을 분석하여 
    객관적이고 전문적인 피드백을 제공하세요.
    - 지원 직무: {job_title}
    - 강점과 약점은 실무적인 관점에서 구체적으로 작성하세요.
    """
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    result = structured_llm.invoke(messages)
    
    return {"evaluation_result": result.dict(), "status": "COMPLETED"}
