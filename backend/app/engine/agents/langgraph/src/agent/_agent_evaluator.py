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
eval_parser = PydanticOutputParser(pydantic_object=EvaluationResult)

# ==========================================
# 3. 프롬프트: 단일 답변 평가 (Evaluator)
# ==========================================

# 간단한 평가 프롬프트 (정답/오답 확인)
SIMPLE_EVALUATOR_SYSTEM_PROMPT = """
you are a quiz correct/incorrect evaluator.
evaluate the user's answer using the question and correct answer. 

respond : correct or incorrect
"""

# 최종 평가 리포트 프롬프트 (세부 평가 항목 포함)
EVALUATOR_SYSTEM_PROMPT = """
당신은 시니어 개발자 면접관입니다.
주어진 면접 질문과 지원자의 답변을 기술적으로 냉정하게 평가하세요.

[필수 평가 항목]
1. 기술적 정확성 (가장 중요)
2. 논리적 흐름 및 명확성
3. 구체적인 예시나 코드 사용 여부

response format:
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


