# global module
from typing import TypedDict, List, Optional
from typing_extensions import Annotated
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# local module
from app.engine.agents.langgraph.src.agent import agent_router, agent_quiz
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
    level: int          # The level of the keyword
    
    # Quiz Context
    current_question: Optional[dict]
    evaluation_result: Optional[dict]
    
    # Navigation
    next_recommendations: List[str]
    user_intent: str         # From Router

# ==========================================
# 2. Nodes
# ==========================================
note = """
    1. router_node : 어떤 대화를 할지 결정
    2. search_keyword_node : 키워드를 DB에서 조회하고 없으면 새로 생성
    3. generate_quiz_node : 키워드 기반으로 퀴즈 생성
    4. chit_chat_node : 일반적인 대화
"""

# 라우터 노드 : 초기 대화 방향 설정 라우터
async def router_node(state: KeywordState):
    """analyzes user intent and prepares for new keyword learning."""
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage):
        return {"user_intent": "WAIT"}
        
    # 의도 분석
    res = await agent_router.route_keyword_intent(last_msg.content, state.get("keyword", "None"))
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
        # 통합 생성 (설명 + 퀴즈)
        kw_data = await agent_quiz.generate_quiz_and_explanation(kw)
        await keyword_service.create_keyword(kw_data)
    elif not kw_data.get("quiz_question"):
        # 퀴즈 정보가 없으면 보충 (기존 데이터 유지)
        new_data = await agent_quiz.generate_quiz_and_explanation(kw)
        kw_data.update({
            "quiz_question": new_data.get("quiz_question"),
            "quiz_options": new_data.get("quiz_options"),
            "quiz_answer": new_data.get("quiz_answer")
        })
        # (Optional) DB 업데이트가 필요하지만, 일단 메모리상에서만 사용
    
    # 퀴즈 정보 추출 및 설정
    quiz_info = {
        "question_text": kw_data.get("quiz_question"),
        "options": kw_data.get("quiz_options"),
        "answer": kw_data.get("quiz_answer")
    }

    msg_content = (
        f"## 📚 Concept: {kw}\n\n"
        f"**Definition**: {kw_data.get('definition')}\n\n"
        f"**Summary**: {kw_data.get('summary')}\n\n"
        f"*(Preparing a quiz for you...)*"
    )
                  
    return {
        "keyword_data": kw_data,
        "current_question": quiz_info, # 다음 단계를 위해 저장
        "messages": [AIMessage(content=msg_content)]
    }

# 퀴즈 생성 노드 : 키워드를 기반으로 퀴즈 생성
async def generate_quiz_node(state: KeywordState):
    """
    [Assessment Phase] Generates a question based on valid content.
    """
    # 이미 search_keyword_node에서 생성된 퀴즈를 가져옴
    question = state.get("current_question")
    
    if not question or not question.get("question_text"):
         return {"messages": [AIMessage(content="Could not generate a quiz at this moment.")]}
    
    # 퀴즈 출력 메시지 구성
    options_text = ""
    if question.get("options"):
        options_text = "\n" + "\n".join([f"- {opt}" for opt in question["options"]])
         
    return {
        "messages": [AIMessage(content=f"**Q. {question['question_text']}**{options_text}")]
    }

async def evaluate_quiz_node(state: KeywordState):
    """
    [Assessment Phase] Evaluates the user's answer. Simple evaluation.
    """

    


# 일반적인 대화를 위한 노드 
async def chit_chat_node(state: KeywordState):
    """
    [Chit-Chat Phase] Handles general conversation.
    """
    response = "도움이 필요하시면 언제든지 말씀해주세요."
    return {"messages": [AIMessage(content=response)]}

# ==========================================
# 3. Edges & Graph
# ==========================================
# 라우터 노드 : 초기 대화 방향 설정 라우터
def route_next(state: KeywordState):
    intent = state.get("user_intent", "CHIT_CHAT")
    if intent == "KEYWORD_SEARCH" or intent == "QUIZ":
        return "search_keyword_node"
    elif intent == "EVALUATE":
        return "evaluate_quiz_node"
    else:
        return "chit_chat_node"
    

workflow = StateGraph(KeywordState)

# Nodes(노드)
workflow.add_node("router", router_node)
workflow.add_node("search_keyword", search_keyword_node)
workflow.add_node("generate_quiz", generate_quiz_node)
workflow.add_node("evaluate_quiz", evaluate_quiz_node)
workflow.add_node("chit_chat", chit_chat_node)

# Edges(-->)
workflow.add_edge(START, "router")
workflow.add_conditional_edges(
    "router", 
    route_next,
    {
        "search_keyword": "search_keyword",
        "chit_chat": "chit_chat",
        "evaluate_quiz": "evaluate_quiz",
        END: END
    }
)
workflow.add_edge("search_keyword", "generate_quiz")
workflow.add_edge("evaluate_quiz", "generate_quiz")
workflow.add_edge("chit_chat", END)
workflow.add_edge("generate_quiz", END)

# Compile
keyword_workflow = workflow.compile()
