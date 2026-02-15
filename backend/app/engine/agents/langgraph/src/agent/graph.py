# global module
from langgraph.graph import StateGraph, START, END

# local module
from app.engine.agents.langgraph.src.agent.state import KeywordState
from app.engine.agents.langgraph.src.agent import agent_router, agent_quiz, agent_keyword, agent_chat

# ==========================================
# 3. Edges & Graph
# ==========================================
# 라우터 노드 : 초기 대화 방향 설정 라우터
def route_next(state: KeywordState):
    intent = state.get("user_intent", "CHIT_CHAT")
    if intent == "KEYWORD_SEARCH" or intent == "QUIZ":
        return "search_keyword"
    elif intent == "EVALUATE":
        return "evaluate_quiz"
    elif intent == "RECOMMEND":
        return "recommend_keyword"
    else:
        return "chit_chat"
    
def pass_fail(state: KeywordState):
    pass_fail = state.get("pass_fail")
    if pass_fail == "pass":
        return "generate_quiz"
    else:
        return "report_star"

workflow = StateGraph(KeywordState)

# Nodes(노드)
workflow.add_node("router", agent_router.router_node)
workflow.add_node("search_keyword", agent_keyword.search_keyword_node)
workflow.add_node("generate_quiz", agent_quiz.generate_quiz_node)
workflow.add_node("evaluate_quiz", agent_quiz.evaluate_quiz_node)
workflow.add_node("report_star", agent_quiz.report_star_node)
workflow.add_node("recommend_keyword", agent_keyword.recommend_keyword_node)
workflow.add_node("info_keyword", agent_keyword.info_keyword_node)
workflow.add_node("chit_chat", agent_chat.chit_chat_node)

# Edges(-->)
workflow.add_edge(START, "router")
workflow.add_conditional_edges(
    "router", 
    route_next,
    {
        "search_keyword": "search_keyword",
        "chit_chat": "chit_chat",
        "evaluate_quiz": "evaluate_quiz",
        "recommend_keyword": "recommend_keyword",
        "info_keyword": "info_keyword",
    }
)
workflow.add_conditional_edges(
    "evaluate_quiz", 
    pass_fail,
    {
        "pass": "generate_quiz",
        "fail": "report_star"
    }
)
workflow.add_edge("search_keyword", "generate_quiz")
workflow.add_edge("report_star", "recommend_keyword")
workflow.add_edge("chit_chat", "recommend_keyword")
workflow.add_edge("recommend_keyword", END)
workflow.add_edge("info_keyword", END)
workflow.add_edge("generate_quiz", END)

# Compile
keyword_workflow = workflow.compile()
