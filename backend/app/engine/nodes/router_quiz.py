from langchain_core.messages import AIMessage, SystemMessage
from pydantic import BaseModel, Field
from typing import Literal

from app.engine.graphs.state import KeywordState
from app.core.llm import get_llm
from app.core.logger import get_logger
from app.engine.nodes.tools import quiz_tools

logger = get_logger("QUIZ_ROUTER")

class QuizRouterOutput(BaseModel):
    action: Literal["EVALUATE_ANSWER", "GENERATE_QUIZ", "CHAT"] = Field(
        description=(
            "EVALUATE_ANSWER: 유저가 퀴즈에 대한 정답이나 풀이를 제출한 경우.\n"
            "GENERATE_QUIZ: 유저가 새로운 문제나 다음 퀴즈를 요구하는 경우.\n"
            "CHAT: 유저가 힌트를 요구하거나 퀴즈와 관련된 보충 설명을 요청하는 경우."
        )
    )

async def quiz_agent_node(state: KeywordState):
    """
    퀴즈 모드 내에서 유저의 발화를 분석하여 정답 평가 / 새 문제 출제 / 자유 대화(힌트/툴 사용)를 분기합니다.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"user_intent": "FINISH"}
        
    last_msg_obj = messages[-1]
    
    # 방어 코드: 사용자 입력이 아닌 경우 (AI가 이미 퀴즈나 리포트를 내뱉은 경우), 라우팅(LLM)을 스킵하고 대기 상태로 넘깁니다.
    if getattr(last_msg_obj, "type", "") != "human":
        return {"user_intent": "FINISH"}
        
    last_msg = last_msg_obj.content
    keyword = state.get("keyword", "알 수 없음")
    current_question = state.get("current_question")
    q_text = current_question.get("question_text") if current_question else "출제된 문제 없음"
    
    llm = get_llm(temperature=0)
    structured_llm = llm.with_structured_output(QuizRouterOutput)
    
    sys_prompt = f"""당신은 유저의 퀴즈 응답을 분석하는 라우터입니다.
현재 학습 주제: {keyword}
현재 출제된 퀴즈: {q_text}

유저의 의도를 분석하여 적절한 액션을 반환하세요:
- EVALUATE_ANSWER: 유저가 정답(숫자, 단답형, 내용 등)을 제시한 경우.
- GENERATE_QUIZ: 유저가 다음 문제, 새로운 문제 등을 명시적으로 요구한 경우.
- CHAT: 정답을 모르겠으니 힌트를 달라고 하거나, 문제 자체에 대한 질문, 툴을 사용한 검색이 필요한 발화인 경우.
"""
    
    try:
        response = await structured_llm.ainvoke([
            SystemMessage(content=sys_prompt),
            ("human", last_msg)
        ])
        action = response.action
    except Exception as e:
        logger.error(f"Quiz Router Error: {e}", exc_info=True)
        action = "CHAT"
        
    logger.info(f"💡 [Quiz Router] Action: {action}")
        
    if action == "CHAT":
        # 순수 라우터 역할만 수행: 생성 로직은 quiz_chat 노드로 위임
        return {"user_intent": "QUIZ_CHAT"}
        
    elif action == "EVALUATE_ANSWER":
        return {"user_intent": "ANSWER"}
        
    elif action == "GENERATE_QUIZ":
        return {"user_intent": "GENERATE_QUIZ"}
        
    return {"user_intent": "FINISH"}