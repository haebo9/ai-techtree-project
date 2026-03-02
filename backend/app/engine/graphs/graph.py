# global module
from langgraph.graph import StateGraph, START, END

# local module
from app.engine.graphs.state import KeywordState
from app.engine.agents import router as agent_router, quiz as agent_quiz, keyword as agent_keyword, chat as agent_chat, report as agent_report

# ==========================================
# 3. Edges & Graph
# ==========================================
# 라우터 노드 : 초기 대화 방향 설정 라우터
def route_next(state: KeywordState):
    intent = state.get("user_intent", "CHIT_CHAT")
    if intent == "KEYWORD_SEARCH" or intent == "QUIZ":
        return "search_keyword"
    elif intent == "ANSWER":
        return "answer_quiz"
    elif intent == "RECOMMEND":
        return "recommend_keyword"
    else:
        return "chit_chat"
    
def quiz_routing(state: KeywordState):
    quiz_count = state.get("quiz_count", 0)
    quiz_min_count = state.get("quiz_min_count", 3)
    quiz_max_count = state.get("quiz_max_count", 8)
    pass_fail_status = state.get("pass_fail")
    
    if quiz_count >= quiz_max_count:
        return "report"
    elif quiz_count < quiz_min_count:
        return "next_quiz"
    else:
        return "next_quiz" if pass_fail_status == "pass" else "report"

workflow = StateGraph(KeywordState)

# Nodes(노드)
workflow.add_node("router", agent_router.router_node)
workflow.add_node("search_keyword", agent_keyword.search_keyword_node)
workflow.add_node("generate_quiz", agent_quiz.generate_quiz_node)
workflow.add_node("answer_quiz", agent_quiz.answer_quiz_node)
workflow.add_node("report_star", agent_report.report_star_node)
workflow.add_node("recommend_keyword", agent_keyword.recommend_keyword_node)
workflow.add_node("chit_chat", agent_chat.chit_chat_node)

# Edges(-->)
workflow.add_edge(START, "router")
workflow.add_conditional_edges(
    "router", 
    route_next,
    {
        "search_keyword": "search_keyword",
        "chit_chat": "chit_chat",
        "answer_quiz": "answer_quiz",
        "recommend_keyword": "recommend_keyword",
    }
)
workflow.add_conditional_edges(
    "answer_quiz",
    quiz_routing,
    {
        "next_quiz": "generate_quiz",
        "report": "report_star"
    }
)
workflow.add_edge("search_keyword", "generate_quiz")
workflow.add_edge("chit_chat", END)
workflow.add_edge("report_star", END)
workflow.add_edge("recommend_keyword", END)
workflow.add_edge("generate_quiz", END)

# Compile
agent_workflow = workflow.compile()
