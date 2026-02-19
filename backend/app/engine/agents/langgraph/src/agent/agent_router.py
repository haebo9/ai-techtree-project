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
    intent: Literal["KEYWORD_SEARCH", "ANSWER", "NAVIGATION", "CHIT_CHAT"] = Field(
        ..., description="Classified intent: KEYWORD_SEARCH, ANSWER, NAVIGATION, CHIT_CHAT"
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
    - Examples: "정답은 2번", "스택입니다", "LIFO 구조", "몰라요"
    - Condition: Valid ONLY if Last System Action was 'ASKED_QUESTION' or similar.

    3. **NAVIGATION**: 
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
    model="gpt-4o-mini", 
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
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage):
        return {"user_intent": "WAIT"}
        
    # 의도 분석
    res = await route_keyword_intent(last_msg.content, state.get("keyword", "None"))
    intent = res.get("intent", "CHIT_CHAT")
    
    updates = {"user_intent": intent}
    
    # 키워드 검색 시 상태 초기화
    if intent == "KEYWORD_SEARCH" and res.get("keyword"):
        updates.update({
            "keyword": res["keyword"],
            "keyword_data": {}, # reset
            "current_question": None # reset
        })
        
    return updates
