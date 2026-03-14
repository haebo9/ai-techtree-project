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
    llm = get_llm(temperature=0)
    structured_llm = llm.with_structured_output(QuizRouterOutput)
    
    keyword = state.get("keyword", "알 수 없음")
    current_question = state.get("current_question")
    q_text = current_question.get("question_text") if current_question else "출제된 문제 없음"
    messages = state.get("messages", [])
    last_msg = messages[-1].content
    
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
        # 힌트나 설명이 필요한 경우 도구가 바인딩된 에이전트가 직접 반응
        agent_llm = get_llm(temperature=0.4).bind_tools(quiz_tools)
        chat_sys_prompt = f"""당신은 친절한 CS 기술 면접관이자 튜터입니다.
주제: {keyword}
출제된 문제: {q_text}

- 유저가 힌트를 요구하거나, 관련 개념을 물어보았습니다.
- 정답을 섣불리 알려주지 말고, 개념의 힌트를 주어 스스로 생각할 수 있도록 유도하세요.
- 필요시 `quiz_tools`의 도구들을 사용하여 추가 정보를 제공하세요.
"""
        agent_msgs = [SystemMessage(content=chat_sys_prompt)] + messages
        ai_response = await agent_llm.ainvoke(agent_msgs)
        return {"messages": [ai_response], "user_intent": "FINISH"}
        
    elif action == "EVALUATE_ANSWER":
        return {"user_intent": "ANSWER"}
        
    elif action == "GENERATE_QUIZ":
        return {"user_intent": "GENERATE_QUIZ"}
        
    return state