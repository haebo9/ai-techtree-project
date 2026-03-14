from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.engine.graphs.state import KeywordState
from app.engine.nodes.schemas_router import KeywordRouterOutput
from app.engine.prompts.router_prompts import ROUTER_SYSTEM_PROMPT
from app.core.llm import get_llm
from app.core.logger import get_logger

from langgraph.prebuilt import ToolNode, tools_condition

logger = get_logger("SUPERVISOR_ROUTER")

# ==========================================
# Prompt Definition & Chain
# ==========================================
router_prompt = ChatPromptTemplate.from_messages([
    ("system", ROUTER_SYSTEM_PROMPT),
    ("human", "{user_input}")
])

llm = get_llm(temperature=0.5)
router_chain = router_prompt | llm | JsonOutputParser(pydantic_object=KeywordRouterOutput)

# ==========================================
# Execution Function
# ==========================================
async def route_keyword_intent(user_input: str, current_keyword: str = "None", last_action: str = "None") -> dict:
    """
    Analyzes user input to determine the next step in the keyword learning graph.
    """
    try:
        result = await router_chain.ainvoke({
            "user_input": user_input,
            "current_keyword": current_keyword,
            "last_action": last_action
        })
        return result
    except Exception as e:
        logger.error(f"⚠️ [KeywordRouter] Error: {e}", exc_info=True)
        # Fallback to CHIT_CHAT if parsing fails
        return {"intent": "CHIT_CHAT", "keyword": None, "reasoning": "Error Fallback"}

# ==========================================
# Nodes & Routing
# ==========================================
# 감독자 노드 : 초기 대화 방향 설정 및 다음 에이전트 결정
async def supervisor_node(state: KeywordState):
    """analyzes user intent and prepares for new keyword learning or routing."""
    
    last_msg = state["messages"][-1]
    
    # [추가] 방금 상태 배열에 들어온 마지막 메시지가 AI의 텍스트 최종 응답이라면,
    # 문답 사이클을 종료하기 위해 라우팅을 우회하고 FINISH를 넘깁니다.
    # if isinstance(last_msg, AIMessage) and not last_msg.tool_calls:
        # return {"user_intent": "FINISH"}
        
    # 디버깅 로그
    logger.info(f"DEBUG: Supervisor started. In-Progress: {state.get('quiz_in_progress')}, \nQuestion: {bool(state.get('current_question'))}")

    # 의도 분석 및 지난 액션 설정
    # 퀴즈 진행 중일 경우 LLM에 컨텍스트로 전달하여 무조건 ANSWER로 처리되도록 유도 (프롬프트 규칙)
    last_action = "QUIZ_IN_PROGRESS" if state.get("quiz_in_progress") else "None"
    current_kw = state.get("keyword") or "None"
    
    res = await route_keyword_intent(last_msg.content, current_kw, last_action)
    intent = res.get("intent", "CHIT_CHAT")
    
    # ⚡ [안전 장치 1] LLM이 'ANSWER'로 오분류하더라도, 현재 진행 중인 퀴즈 메모리가 없다면 에러 방지를 위해 'RECOMMEND'나 'CHIT_CHAT'으로 우회시킵니다.
    if intent == "ANSWER" and not state.get("current_question"):
        intent = "RECOMMEND"
        
    # ⚡ [안전 장치 2] LLM이 'KEYWORD_SEARCH'로 판단했으나 실질적으로 분석한 keyword가 없는 경우('다른건?' 등), 에러를 피하기 위해 추천으로 돌립니다.
    if intent == "KEYWORD_SEARCH" and not res.get("keyword"):
        intent = "RECOMMEND"
    
    updates = {"user_intent": intent}
    
    # 키워드 검색 시 상태 초기화
    if intent == "KEYWORD_SEARCH" and res.get("keyword"):
        updates.update({
            "keyword": res["keyword"],
            "keyword_data": {}, # reset
            "current_question": None, # reset
            "quiz_count": 0, # reset
            "quiz_pass_count": 0, # reset
            "level": 0, # reset
            "quiz_history": [] # reset
        })
        
    return updates