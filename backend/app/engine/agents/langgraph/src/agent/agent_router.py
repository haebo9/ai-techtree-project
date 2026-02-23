from typing import Literal, Optional
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# ==========================================
# Router Schema
# ==========================================
class KeywordRouterOutput(BaseModel):
    """
    User intent classification for Keyword-based learning flow.
    """
    intent: Literal["KEYWORD_SEARCH", "ANSWER", "RECOMMEND", "CHIT_CHAT"] = Field(
        ..., description="Classified intent: KEYWORD_SEARCH, ANSWER, RECOMMEND, CHIT_CHAT"
    )
    keyword: Optional[str] = Field(
        None, description="Extracted keyword if intent is KEYWORD_SEARCH (e.g., 'BFS', 'Docker')"
    )
    reasoning: str = Field(..., description="Reason for classification")

# ==========================================
# Prompt Definition
# ==========================================
ROUTER_SYSTEM_PROMPT = """
    You are the 'Router' for an AI TechTree Learning Agent. 
    Your goal is to accurately classify user intent and extract technical keywords from Korean/English input.

    [Context]
    - Current Keyword: {current_keyword}
    - Last System Action: {last_action}

    [Intent Classification Rules]
    **CRITICAL RULE FOR QUIZ**:
    - If **Last System Action** is "**QUIZ_IN_PROGRESS**":
        - **DEFAULT Intent** is **ANSWER**.
        - Treat ANY input (even explicitly generic commands like "Stop", "Quit", "Change topic", "그만", "다른거 할래") as an **ANSWER**.
        - This ensures the quiz is graded (as incorrect/given up) and the session is properly closed.
        - **EXCEPTION**: Only if the user asks a completely unrelated question like "오늘 날씨 어때?", classify as **CHIT_CHAT**. But "다른거 공부할래" is **ANSWER** (meaning "I give up on this quiz").
        - Example: 
            - Context: QUIZ_IN_PROGRESS
            - Input: "Docker" -> Intent: **ANSWER**
            - Input: "정답은 Docker" -> Intent: **ANSWER**
            - Input: "다른거 공부할래" -> Intent: **ANSWER** (Will be treated as incorrect/stop)
            - Input: "그만" -> Intent: **ANSWER**

    1. **KEYWORD_SEARCH**: 
    - User wants to learn about a specific **Computer Science or Software Development** concept/tool.
    - **CRITICAL**: If the keyword is NOT related to CS/Dev (e.g., "History", "Cooking", "Celebrity"), classify as **CHIT_CHAT**.
    - ACTION: Extract the core technical term as 'keyword'.
    - RULE: Remove Korean postpositions and extract ONLY the noun.
    - RULE: Translate Korean technical terms to standard English (e.g., "자바" -> "Java").
    - Examples:
        - "도커" -> Intent: KEYWORD_SEARCH, Keyword: "Docker" (CS/Dev O)
        - "김치찌개 레시피" -> Intent: CHIT_CHAT (CS/Dev X)
        - "BFS 알고리즘" -> Intent: KEYWORD_SEARCH, Keyword: "BFS" (CS/Dev O)
        - "아이유" -> Intent: CHIT_CHAT (CS/Dev X)

    2. **ANSWER**: 
    - User is responding to a question asked by the system.
    - Examples: "정답은 2번", "스택입니다", "LIFO 구조", "몰라요", "Docker"
    - Condition: **MUST prioritize this intent** if Last System Action was 'ASKED_QUESTION' or 'QUIZ_IN_PROGRESS'.
    - Even if the input is a keyword (e.g., "Python"), if it's an answer to a question, classify as **ANSWER**, NOT KEYWORD_SEARCH.

    3. **RECOMMEND**: 
    - User asks for recommendations or next steps WITHOUT specifying a concrete topic.
    - Examples: "다음", "넘어가자", "추천해줘", "Next", "Pass"

    4. **CHIT_CHAT**: 
    - Greetings, general conversation, OR **Non-CS/Dev topics**.
    - Examples: "안녕", "오늘 날씨 어때?", "요리법 알려줘"

    [Output Format]
    Return a JSON object conforming to the KeywordRouterOutput schema.
"""

router_prompt = ChatPromptTemplate.from_messages([
    ("system", ROUTER_SYSTEM_PROMPT),
    ("human", "{user_input}")
])

# ==========================================
# Model Setup
# ==========================================
api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-4.1", 
    temperature=0.5,
    api_key=api_key
)

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
        print(f"⚠️ [KeywordRouter] Error: {e}")
        # Fallback to CHIT_CHAT if parsing fails
        return {"intent": "CHIT_CHAT", "keyword": None, "reasoning": "Error Fallback"}

# ==========================================
# Nodes
# ==========================================
from langchain_core.messages import AIMessage
from app.engine.agents.langgraph.src.agent.state import KeywordState

# 라우터 노드 : 초기 대화 방향 설정 라우터
async def router_node(state: KeywordState):
    """analyzes user intent and prepares for new keyword learning."""
    
    # ⚡ [강제 라우팅] 퀴즈 진행 중일 때는 LLM을 거치지 않고 무조건 ANSWER로 처리합니다.
    if state.get("quiz_in_progress", False):
        return {"user_intent": "ANSWER"}
        
    last_msg = state["messages"][-1]
        
    # 의도 분석
    last_action = "None"

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
