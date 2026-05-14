from langgraph.graph import StateGraph, START, END

from app.engine.graphs.state import InterviewState
from app.engine.nodes.manager import manager_agent_node, manager_finalize_node, manager_tool_node
from app.engine.nodes.evaluator import evaluator_node


# ==========================================
# 라우팅(Edges) 로직
# ==========================================
def route_start(state: InterviewState):
    """
    Realtime 면접 전에는 manager가 컨텍스트를 준비하고,
    면접 종료 후에는 evaluator가 전체 transcript를 평가합니다.
    """
    status = state.get("status", "IN_PROGRESS")
    if status == "EVALUATING":
        return "evaluate"
    return "manager_agent"

def route_manager(state: InterviewState):
    """
    manager_agent가 툴을 호출했으면 tools로, 
    그렇지 않으면 manager_finalize로 이동합니다.
    """
    messages = state.get("messages", [])
    if messages and hasattr(messages[-1], "tool_calls") and messages[-1].tool_calls:
        return "tools"
    return "manager_finalize"

# ==========================================
# 워크플로우 조립
# ==========================================
workflow = StateGraph(InterviewState)

# 1. 노드 추가
workflow.add_node("manager_agent", manager_agent_node)
workflow.add_node("tools", manager_tool_node)
workflow.add_node("manager_finalize", manager_finalize_node)
workflow.add_node("evaluate", evaluator_node)

# 2. 흐름 연결
workflow.add_conditional_edges(
    START,
    route_start,
    {
        "manager_agent": "manager_agent",
        "evaluate": "evaluate",
    }
)
workflow.add_conditional_edges(
    "manager_agent",
    route_manager,
    {
        "tools": "tools",
        "manager_finalize": "manager_finalize"
    }
)
workflow.add_edge("tools", "manager_agent")
workflow.add_edge("manager_finalize", END)
workflow.add_edge("evaluate", END)

# 3. 그래프 컴파일
# LangGraph Studio/Cloud 모니터링용 (Checkpointer 없음)
studio_workflow = workflow.compile()

# 로컬 FastAPI 백엔드용 (MemorySaver 포함)
def get_interview_workflow():
    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
