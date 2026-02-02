from typing import Literal, Optional, TypedDict
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# ==========================================
# 1. 라우터 출력 구조 (Schema)
# ==========================================
class RouterOutput(BaseModel):
    """
    사용자 입력 분석 결과
    """
    intent: Literal["ANSWER", "NEXT_QUESTION", "CHANGE_TOPIC", "CONSULT", "QUIT"] = Field(
        ..., description="사용자의 주요 의도 (답변, 다음 질문, 주제 변경, 상담, 종료)"
    )
    topic: Optional[str] = Field(
        None, description="CHANGE_TOPIC인 경우 변경할 새로운 주제 (예: 'Python', 'React'). 그 외엔 null."
    )
    reasoning: str = Field(..., description="이 분류를 선택한 간략한 이유")

# ==========================================
# 2. 프롬프트 정의
# ==========================================
ROUTER_SYSTEM_PROMPT = """
당신은 AI Interviewer System의 'Router(방향 결정자)'입니다.
사용자의 최근 발화와 대화 맥락을 분석하여 다음 행동을 결정하세요.

[Context]
- 현재 주제: {current_topic}
- 마지막 질문: {last_question}

[Intent 분류 가이드]
1. ANSWER: 면접 질문에 대한 답변을 시도함 (오답이나 "모르겠다" 포함)
2. NEXT_QUESTION: 면접을 진행하거나 새로운 문제를 요청함 (예: "패스", "다음", "문제 내줘", "시작하자")
3. CHANGE_TOPIC: 특정 주제로 면접을 원함 (예: "자바로 할래", "DB 문제 줘", "에이전트 관련 문제 내줘")
4. CONSULT: 면접 문제 풀이가 아닌 일반 대화, 정보 검색 요청, 질문 (예: "LangGraph 정보 찾아줘", "이게 뭐야?", "공부법 알려줘")
5. QUIT: 인터뷰 종료 요청 (예: "그만", "종료")

[주의사항]
- 사용자가 답을 시도했다면 무조건 ANSWER입니다.
- "문제 내줘", "시작해줘", "면접 볼래" 등, **문제를 풀겠다는 의도**가 보이면 반드시 NEXT_QUESTION 또는 CHANGE_TOPIC으로 분류하세요. (CONSULT 아님!)
- "~~ 정보 찾아줘" 같은 검색 요청만 CONSULT입니다.
- "에이전트 관련 문제 내줘" -> CHANGE_TOPIC (topic="Agent")
- JSON 형식으로만 응답하세요.
"""

router_prompt = ChatPromptTemplate.from_messages([
    ("system", ROUTER_SYSTEM_PROMPT),
    ("human", "{user_input}")
])

# ==========================================
# 3. 모델 및 체인 설정
# ==========================================
# 라우팅은 속도가 중요하므로 가벼운 모델 권장 (gpt-4o-mini 등)
api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0.0, # 분류 작업은 일관성이 중요
    api_key=api_key
)

router_chain = router_prompt | llm | JsonOutputParser(pydantic_object=RouterOutput)

# ==========================================
# 4. 실행 함수 (Execution Function)
# ==========================================
async def route_user_input(user_input: str, current_topic: str = "General", last_question: str = "") -> dict:
    """
    사용자 입력을 분석하여 그래프의 다음 경로(Intent)를 반환합니다.
    """
    try:
        result = await router_chain.ainvoke({
            "user_input": user_input,
            "current_topic": current_topic,
            "last_question": last_question
        })
        return result
    except Exception as e:
        # 파싱 에러나 API 오류 시 기본값(상담 모드)으로 안전하게 처리
        print(f"⚠️ [Router] Error routing input: {e}")
        return {"intent": "CONSULT", "topic": None, "reasoning": "System Error Fallback"}
