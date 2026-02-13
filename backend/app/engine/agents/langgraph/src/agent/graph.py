# global module
from typing import TypedDict, List, Optional
from typing_extensions import Annotated
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# local module
from app.engine.agents.langgraph.src.agent.agent_router import route_keyword_intent
from app.engine.agents.langgraph.src.agent.agent_quiz import generate_keyword_questions
from app.services.keyword_service import keyword_service

# ==========================================
# 1. State Definition
# ==========================================
# 키워드 관련 상태 저장 클래스
class KeywordState(TypedDict, total=False):
    """
    State for the Keyword-Driven Learning Flow.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User Context
    user_id: str
    user_db_id: str
    
    # Current Focus
    keyword: str             # The active keyword
    keyword_data: dict       # Extracted/Generated content (def, summary)
    
    # Quiz Context
    current_question: Optional[dict]
    evaluation_result: Optional[dict]
    
    # Navigation
    next_recommendations: List[str]
    user_intent: str         # From Router

# ==========================================
# 2. Nodes
# ==========================================
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

# 사용자 요청과 관련된 키워드를 DB에서 찾고 없으면 새롭게 생성
async def search_keyword_node(state: KeywordState):
    """
    [Content Phase] 
    1. Searches (or generates) info for the keyword.
    2. Explains it to the user.
    """
    kw = state.get("keyword")
    if not kw:
        return {"messages": [AIMessage(content="Please specify a keyword to learn.")]}
    
    # DB 조회 시도
    kw_data = await keyword_service.get_keyword(kw)
    
    # 없으면 새로 생성 후 저장
    if not kw_data:
        kw_data = await explain_keyword(kw)
        await keyword_service.create_keyword(kw_data)
    
    msg_content = (
        f"## 📚 Concept: {kw}\n\n"
        f"**Definition**: {kw_data.get('definition')}\n\n"
        f"**Summary**: {kw_data.get('summary')}\n\n"
        f"*(Preparing a quiz for you...)*"
    )
                  
    return {
        "keyword_data": kw_data,
        "messages": [AIMessage(content=msg_content)]
    }

# 퀴즈 생성 노드 : 키워드를 기반으로 퀴즈 생성
async def generate_quiz_node(state: KeywordState):
    """
    [Assessment Phase] Generates a question based on valid content.
    """
    kw = state.get("keyword")
    kw_data = state.get("keyword_data", {})
    
    # Use definitions to generate targeted Q
    questions = await generate_keyword_questions(
        keyword=kw,
        definition=kw_data.get("definition", ""),
        level="Intermediate" # Could comprise from user profile
    )
    
    if not questions:
         return {"messages": [AIMessage(content="Could not generate a quiz at this moment.")]}
         
    question = questions[0]
    return {
        "current_question": question,
        "messages": [AIMessage(content=f"**Q. {question['question_text']}**")]
    }

# ==========================================
# 3. Edges & Graph
# ==========================================
# 라우터 노드 : 초기 대화 방향 설정 라우터
def route_next(state: KeywordState):
    intent = state.get("user_intent")
    if intent == "KEYWORD_SEARCH":
        return "search_keyword_node"
    elif intent == "QUIZ":
        return "generate_quiz"
    else:
        return END
    

workflow = StateGraph(KeywordState)

# Nodes(노드)
workflow.add_node("router", router_node)
workflow.add_node("search_keyword_node", search_keyword_node)
workflow.add_node("generate_quiz_node", generate_quiz_node)

# Edges(-->)
workflow.add_edge("router", "search_keyword_node")
workflow.add_edge("search_keyword_node", "generate_quiz_node")
workflow.add_edge("generate_quiz_node", END)

# Entry Point(시작점)
workflow.set_entry_point("router")

# Compile
keyword_workflow = workflow.compile()
