from langgraph.graph import StateGraph, START, END
from app.engine.graphs.state import InterviewState

# 각 노드(에이전트 역할) 모듈 임포트
from app.engine.nodes.interviewer import interviewer_node
from app.engine.nodes.evaluator import evaluator_node

def route_interview(state: InterviewState):
    """
    상태에 따라 대화를 이어갈지, 평가로 넘어갈지 라우팅합니다.
    """
    status = state.get("status", "IN_PROGRESS")
    if status == "EVALUATING":
        return "evaluate"
    return "interview"

# ==========================================
# 워크플로우 조립
# ==========================================
workflow = StateGraph(InterviewState)

# 1. 노드 추가
workflow.add_node("interview", interviewer_node)
workflow.add_node("evaluate", evaluator_node)

# 2. 흐름 연결
workflow.add_edge(START, "interview")
workflow.add_conditional_edges(
    "interview",
    route_interview,
    {
        "interview": "interview", 
        "evaluate": "evaluate"    
    }
)
workflow.add_edge("evaluate", END)

# 3. 그래프 컴파일
interview_workflow = workflow.compile()
