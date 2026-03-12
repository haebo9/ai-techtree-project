# global module
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

# local module
from app.engine.graphs.state import KeywordState
from app.engine.agents import router as agent_router, quiz as agent_quiz, keyword as agent_keyword, chat as agent_chat, report as agent_report

# ==========================================
# 1. Dummy Nodes (빈 노드 정의)
# ==========================================
async def supervisor_node(state: KeywordState):
    """
    중앙 감독자: 사용자의 의도를 분석하고 다음에 어떤 에이전트를 호출할지 결정합니다.
    (실제 구현 시 LLM이 호출되어 next_agent를 결정하게 됩니다.)
    """
    print("--- SUPERVISOR: 호출됨 ---")

    intent = state.get("user_intent", "CHIT_CHAT")
    if intent == "KEYWORD_SEARCH" or intent == "QUIZ":
        return "search_keyword"
    elif intent == "ANSWER":
        return "answer_quiz"
    elif intent == "RECOMMEND":
        return "recommend_keyword"
    else:
        return "chit_chat"

async def quiz_agent_node(state: KeywordState): 
    return state

# ==========================================
# 2. Router (조건부 에지 로직)
# ==========================================
# 라우터 노드 : 초기 대화 방향 설정 라우터
def route_next(state: KeywordState):
    intent = state.get("user_intent")
    if intent == "KEYWORD_SEARCH" or intent == "QUIZ":
        return "search_keyword"
    elif intent == "ANSWER":
        return "answer_quiz"
    
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

# ==========================================
# 3. Edges & Graph
# ==========================================
workflow = StateGraph(KeywordState)

# Nodes(노드)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("quiz_agent", quiz_agent_node)
workflow.add_node("search_keyword", agent_keyword.search_keyword_node)
workflow.add_node("generate_quiz", agent_quiz.generate_quiz_node)
workflow.add_node("answer_quiz", agent_quiz.answer_quiz_node)
workflow.add_node("report_star", agent_report.report_star_node)
workflow.add_node("recommend_keyword", agent_keyword.recommend_keyword_node)
workflow.add_node("chit_chat", agent_chat.chit_chat_node)

# Edges(-->)
workflow.add_edge(START, "supervisor")
workflow.add_conditional_edges(
    "supervisor",
    supervisor_node,
    {
        "quiz_agent": "quiz_agent",
        "recommend_keyword": "recommend_keyword",
        "chit_chat": "chit_chat",
        "exit": END
    }
)
workflow.add_conditional_edges(
    "quiz_agent", 
    route_next,
    {
        "search_keyword": "search_keyword",
        "answer_quiz": "answer_quiz",
        "next_quiz": "generate_quiz",
        "report": "report_star"
    }
)

# back to supervisor
workflow.add_edge("chit_chat", "supervisor")
workflow.add_edge("recommend_keyword", "supervisor")
workflow.add_edge("quiz_agent", "supervisor")

# quiz_agent
workflow.add_edge("report_star", "quiz_agent")
workflow.add_edge("answer_quiz", "quiz_agent")
workflow.add_edge("search_keyword", "quiz_agent")
workflow.add_edge("generate_quiz", "quiz_agent")

# Compile
# checkpointer = InMemorySaver()
# agent_workflow = workflow.compile(checkpointer=checkpointer)

# LangGraph API를 위한 컴파일 (checkpointer 제거)
agent_workflow = workflow.compile()
