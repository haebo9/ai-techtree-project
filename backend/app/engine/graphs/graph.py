# global module
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode, tools_condition

# local module
from app.engine.graphs.state import KeywordState
from app.engine.agents import router as agent_router, quiz as agent_quiz, keyword as agent_keyword, chat as agent_chat, report as agent_report
from app.api_mcp.tools import MCP_TOOLS

# ==========================================
# 1. SUPERVISOR and SubGraph Nodes
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
    # 1. LLM에 도구 바인딩 (추천 등 도구 사용 가능)
    llm = get_llm().bind_tools(MCP_TOOLS)
    
    # 2. 면접관 페르소나와 현재 상황 전달
    # (유저의 정답 여부에 따라 심화 질문할지, 툴을 써서 설명해줄지 판단 유도)
    prompt = "당신은 CS 면접관입니다. 유저의 답변을 보고 꼬리질문을 할지, 다음 주제로 넘어갈지, 혹은 툴을 써서 개념을 설명해줄지 결정하세요."
    
    # 여기서 LLM 호출...
    # response = await llm.ainvoke(state["messages"])
    # return {"messages": [response]}
    return state # 일단 구조 유지를 위해 return

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
supervisor_tools_node = ToolNode(tools=MCP_TOOLS)
quiz_tools_node = ToolNode(tools=[])

# Nodes(노드)
workflow.add_node("SUPERVISOR", supervisor_node)
workflow.add_node("QUIZ", quiz_agent_node)
workflow.add_node('supervisor_tools', supervisor_tools_node)
workflow.add_node('quiz_tools', quiz_tools_node)

workflow.add_node("search_keyword", agent_keyword.search_keyword_node)
workflow.add_node("generate_quiz", agent_quiz.generate_quiz_node)
workflow.add_node("answer_quiz", agent_quiz.answer_quiz_node)
workflow.add_node("report_star", agent_report.report_star_node)
workflow.add_node("recommend_keyword", agent_keyword.recommend_keyword_node)
workflow.add_node("chit_chat", agent_chat.chit_chat_node)

# Edges(-->)
workflow.add_edge(START, "SUPERVISOR")
workflow.add_conditional_edges(
    "SUPERVISOR",
    supervisor_node,
    {
        "QUIZ": "QUIZ",
        "recommend_keyword": "recommend_keyword",
        "chit_chat": "chit_chat",
        "exit": END
    }
)
workflow.add_conditional_edges(
    "QUIZ", 
    route_next,
    {
        "quiz_tools": "quiz_tools",
        "search_keyword": "search_keyword",
        "answer_quiz": "answer_quiz",
    }
)
workflow.add_conditional_edges(
    "SUPERVISOR",
    tools_condition, 
    {
        "supervisor_tools": "supervisor_tools",
        "__end__": END
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
workflow.add_edge("QUIZ", "SUPERVISOR")
workflow.add_edge("supervisor_tools", "SUPERVISOR")
workflow.add_edge("quiz_tools", "QUIZ")


# QUIZ
workflow.add_edge("report_star", "QUIZ")
workflow.add_edge("generate_quiz", "QUIZ")
workflow.add_edge("search_keyword", "generate_quiz")

# Compile
# checkpointer = InMemorySaver()
# agent_workflow = workflow.compile(checkpointer=checkpointer)

# LangGraph API를 위한 컴파일 (checkpointer 제거)
agent_workflow = workflow.compile()
