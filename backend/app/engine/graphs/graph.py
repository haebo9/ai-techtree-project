from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.engine.graphs.state import InterviewState
from app.engine.nodes.interviewer import interviewer_node
from app.engine.nodes.evaluator import evaluator_node
from app.engine.tools.job_search import search_korean_job_postings

# ==========================================
# 도구(Tools) 노드 설정
# ==========================================
tools = [search_korean_job_postings]
tools_node = ToolNode(tools)

# ==========================================
# 라우팅(Edges) 로직
# ==========================================
def route_interviewer(state: InterviewState):
    """
    면접관 AI의 결과에 따라 툴을 실행할지, 대기를 할지, 평가로 넘어갈지 라우팅합니다.
    """
    messages = state.get("messages", [])
    
    # 1. 툴 호출(tool_calls)이 발생한 경우 ToolNode로 이동
    if messages and hasattr(messages[-1], "tool_calls") and messages[-1].tool_calls:
        return "tools"
        
    # 2. 면접 종료 상태인 경우 Evaluator로 이동
    status = state.get("status", "IN_PROGRESS")
    if status == "EVALUATING":
        return "evaluate"
        
    # 3. 추가 동작이 없다면 사용자 응답을 대기하기 위해 그래프 일시 정지(END)
    return END

# ==========================================
# 워크플로우 조립
# ==========================================
workflow = StateGraph(InterviewState)

# 1. 노드 추가
workflow.add_node("interviewer", interviewer_node)
workflow.add_node("tools", tools_node)
workflow.add_node("evaluate", evaluator_node)

# 2. 흐름 연결
workflow.add_edge(START, "interviewer")

# 면접관 노드 이후의 조건부 라우팅 (에이전틱 루프)
workflow.add_conditional_edges(
    "interviewer",
    route_interviewer,
    {
        "tools": "tools",       # 도구 사용
        "evaluate": "evaluate", # 평가 단계로 이동
        END: END                # 사용자 답변 대기
    }
)

# 툴 실행이 끝나면 다시 면접관 노드로 돌아와 결과를 바탕으로 대화 생성
workflow.add_edge("tools", "interviewer")
workflow.add_edge("evaluate", END)

# 3. 그래프 컴파일 (추후 Memory Checkpointer 추가)
interview_workflow = workflow.compile()

