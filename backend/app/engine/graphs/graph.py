# global module
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import tools_condition
from langchain_core.messages import AIMessage

# local module
from app.engine.graphs.state import KeywordState
from app.engine.nodes import router_supervisor, router_quiz
from app.engine.nodes import agent_quiz, agent_keyword, agent_chat, agent_report
from app.engine.nodes import tools

# ==========================================
# Router (조건부 에지 로직)
# ==========================================
# Supervisor Routing
def route_supervisor(state: KeywordState):
    """Supervisor 상태가 업데이트 된 후 다음 에이전트/노드를 결정합니다."""
    
    # 1. tools_condition 기능 활용 (Agent Tool Call 여부 판단)
    # tools_condition은 툴 호출이 있으면 "tools", 없으면 "__end__"를 반환합니다.
    route = tools_condition(state)
    if route == "tools":
        return "supervisor_tools"
        
    # 2. Intent 기반 라우팅 ("__end__" 일 경우)
    intent = state.get("user_intent", "CHIT_CHAT")
    
    if intent == "FINISH":
        return "__end__"
    elif intent in ["KEYWORD_SEARCH", "ANSWER", "QUIZ"]:
        return "QUIZ" # 서브그래프 또는 퀴즈 에이전트 노드로 이동
    elif intent == "RECOMMEND":
        return "recommend_keyword"
    else:
        return "chit_chat"

# 라우터 노드 : 초기 대화 방향 설정 라우터
def quiz_next(state: KeywordState):
    # 마지막 메시지가 AI 응답일 경우 더 사이클을 돌지 않고 SUPERVISOR로 제어권을 넘깁니다.
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage) and not messages[-1].tool_calls:
        return "FINISH"

    intent = state.get("user_intent")
    if intent in ["KEYWORD_SEARCH", "QUIZ"]:
        return "search_keyword"
    elif intent == "GENERATE_QUIZ":
        return "generate_quiz"
    elif intent == "ANSWER":
        return "answer_quiz"
    elif intent == "QUIZ_CHAT":
        return "quiz_chat"
    
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
# Edges & Graph
# ==========================================
workflow = StateGraph(KeywordState)

# Nodes(노드)
workflow.add_node("SUPERVISOR", router_supervisor.supervisor_node)
workflow.add_node("QUIZ", router_quiz.quiz_agent_node)
workflow.add_node('supervisor_tools', tools.supervisor_tools_node)
workflow.add_node('quiz_tools', tools.quiz_tools_node)

workflow.add_node("search_keyword", agent_keyword.search_keyword_node)
workflow.add_node("generate_quiz", agent_quiz.generate_quiz_node)
workflow.add_node("answer_quiz", agent_quiz.answer_quiz_node)
workflow.add_node("report_star", agent_report.report_star_node)
workflow.add_node("recommend_keyword", agent_keyword.recommend_keyword_node)
workflow.add_node("chit_chat", agent_chat.chit_chat_node)
workflow.add_node("quiz_chat", agent_quiz.quiz_chat_node)

# Edges(-->)
workflow.add_edge(START, "SUPERVISOR")
workflow.add_conditional_edges(
    "SUPERVISOR",
    route_supervisor,
    {
        "supervisor_tools": "supervisor_tools",
        "QUIZ": "QUIZ",
        "recommend_keyword": "recommend_keyword",
        "chit_chat": "chit_chat",
        "__end__": END
    }
)
workflow.add_conditional_edges(
    "QUIZ", 
    quiz_next,
    {
        "quiz_tools": "quiz_tools",
        "search_keyword": "search_keyword",
        "generate_quiz": "generate_quiz",
        "answer_quiz": "answer_quiz",
        "quiz_chat": "quiz_chat",
        "FINISH": "SUPERVISOR"
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

# back to SUPERVISOR
workflow.add_edge("chit_chat", "SUPERVISOR")
workflow.add_edge("recommend_keyword", "SUPERVISOR")
workflow.add_edge("supervisor_tools", "SUPERVISOR")
workflow.add_edge("quiz_tools", "QUIZ")
workflow.add_edge("quiz_chat", "SUPERVISOR")


# QUIZ
workflow.add_edge("report_star", "SUPERVISOR")
workflow.add_edge("generate_quiz", "SUPERVISOR")
workflow.add_edge("search_keyword", "generate_quiz")

# Compile
checkpointer = InMemorySaver()
agent_workflow = workflow.compile(checkpointer=checkpointer)

# LangGraph API를 위한 컴파일 (checkpointer 제거)
# agent_workflow = workflow.compile()
