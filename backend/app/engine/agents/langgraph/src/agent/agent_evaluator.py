from typing import List, Optional
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# ==========================================
# 1. 데이터 구조 (Schema)
# ==========================================
class EvaluationResult(BaseModel):
    """단일 답변 평가 결과"""
    score: int = Field(description="정확도 및 논리성에 기반한 점수 (0-100)")
    is_passed: bool = Field(description="합격 여부 (70점 이상이면 True)")
    reason: str = Field(description="기술적인 평가 결과 (감점 요인 등)")
    feedback: str = Field(description="사용자에게 전달할 건설적인 피드백")
    better_answer: Optional[str] = Field(description="더 나은 구현이나 설명이 있다면 제안")

class InterviewResult(BaseModel):
    """전체 인터뷰 종합 분석 리포트"""
    total_score: int = Field(description="종합 기술 역량 점수 (0-100)")
    tier_level: str = Field(description="추정 실력 티어 (예: Junior, Intermediate, Senior)")
    strengths: List[str] = Field(description="발견된 기술적 강점 목록")
    weaknesses: List[str] = Field(description="발견된 기술적 약점 목록")
    study_guide: List[str] = Field(description="향후 학습을 위한 추천 가이드 목록")

# ==========================================
# 2. 모델 및 파서 설정
# ==========================================
api_key = os.getenv("OPENAI_API_KEY")

# 평가 및 분석은 엄격하고 객관적이어야 하므로 temperature=0 (결정론적 출력)
llm = ChatOpenAI(
    model="gpt-4o", 
    temperature=0,  
    api_key=api_key
)

eval_parser = PydanticOutputParser(pydantic_object=EvaluationResult)
report_parser = PydanticOutputParser(pydantic_object=InterviewResult)

# ==========================================
# 3. 프롬프트: 단일 답변 평가 (Evaluator)
# ==========================================
EVALUATOR_SYSTEM_PROMPT = """
당신은 시니어 개발자 면접관입니다.
주어진 면접 질문과 지원자의 답변을 기술적으로 냉정하게 평가하세요.

[필수 평가 항목]
1. 기술적 정확성 (가장 중요)
2. 논리적 흐름 및 명확성
3. 구체적인 예시나 코드 사용 여부

다음의 JSON 형식으로만 응답하세요:
{format_instructions}
"""

eval_prompt = ChatPromptTemplate.from_messages([
    ("system", EVALUATOR_SYSTEM_PROMPT),
    ("human", """
    [질문]: {question}
    [평가 기준]: {evaluation_criteria}
    [지원자 답변]: {user_answer}
    
    위 내용을 바탕으로 평가를 진행해주세요.
    """),
])

evaluator_chain = eval_prompt | llm | eval_parser

# ==========================================
# 4. 프롬프트: 종합 리포트 (Reporter)
# ==========================================
REPORT_SYSTEM_PROMPT = """
당신은 AI TechTree의 최종 평가관입니다.
지원자의 전체 인터뷰 로그를 분석하여 종합적인 개발 역량을 검증하세요.

[분석 포인트]
1. 답변의 일관성과 깊이를 보았을 때, 어느 정도의 Tier(Junior/Middle/Senior)에 해당하는지 판단하세요.
2. 잘 아는 분야(강점)와 모르는 분야(약점)를 명확히 구분하세요.
3. 학습 가이드는 구체적인 주제나 기술 키워드로 제안하세요.

다음의 JSON 형식으로만 응답하세요:
{format_instructions}
"""

report_prompt = ChatPromptTemplate.from_messages([
    ("system", REPORT_SYSTEM_PROMPT),
    ("human", """
    [전체 인터뷰 로그]
    {full_log}
    """),
])

report_chain = report_prompt | llm | report_parser

# ==========================================
# 5. 실행 함수 (Execution Functions)
# ==========================================

async def evaluate_answer(
    question: str, 
    user_answer: str, 
    model_answer: str = "N/A", 
    evaluation_criteria: list = []
) -> dict:
    """
    지원자의 단일 답변을 채점하고 피드백을 생성합니다.
    """
    try:
        criteria_text = ", ".join(evaluation_criteria) if evaluation_criteria else "없음"
        
        result = await evaluator_chain.ainvoke({
            "question": question,
            "user_answer": user_answer,
            "evaluation_criteria": criteria_text,
            "format_instructions": eval_parser.get_format_instructions()
        })
        return result.model_dump()
        
    except Exception as e:
        print(f"⚠️ [Evaluator] Error evaluating answer: {e}")
        # 실패 시 기본값 반환
        return {"score": 0, "is_passed": False, "feedback": "평가 중 시스템 오류가 발생했습니다. 다시 시도해주세요."}

async def analyze_interview_result(conversation_history: List[str]) -> dict:
    """
    인터뷰 전체 로그를 분석하여 종합 리포트를 생성합니다.
    """
    try:
        full_log = "\n".join(conversation_history)
        
        result = await report_chain.ainvoke({
            "full_log": full_log,
            "format_instructions": report_parser.get_format_instructions()
        })
        return result.model_dump()
        
    except Exception as e:
        print(f"⚠️ [Evaluator] Error analyzing report: {e}")
        return {
            "total_score": 0, 
            "tier_level": "Unknown", 
            "strengths": [], 
            "weaknesses": ["분석 실패"], 
            "study_guide": ["리포트 생성 중 오류가 발생했습니다."]
        }
