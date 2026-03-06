# global module
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Optional

# 1. State Definition
class KeywordState(TypedDict): 
    user_id: str
    user_intent: Optional[str] # Routing을 위한 의도 저장

# 2. Dummy Nodes
def router_node(state: KeywordState): 
    # v1.0: 사용자 의도를 분석하여 검색(tools) 혹은 대화(llm) 선택
    return {"user_intent": "info"} # 예시로 info 반환

def tools_node(state: KeywordState): 
    # v1.0: MCP 도구를 통한 정보 검색 수행
    return state

def chat_model_node(state: KeywordState): 
    # v1.0: 최종 답변 생성
    return state

# 3. Routing Logic
def route_v1(state: KeywordState):
    intent = state.get("user_intent")
    if intent == "info":
        return "tools"
    elif intent == "exit":
        return "end"
    return "chat_model"

# 4. Workflow Construction
workflow = StateGraph(KeywordState)

# Nodes
workflow.add_node("router", router_node)
workflow.add_node("tools", tools_node)
workflow.add_node("chat_model", chat_model_node)

# Edges
workflow.add_edge(START, "router")

workflow.add_conditional_edges(
    "router",
    route_v1,
    {
        "tools": "tools",
        "chat_model": "chat_model",
    }
)

workflow.add_edge("tools", "chat_model")
workflow.add_edge("chat_model", END)

# 5. Compile
agent_workflow = workflow.compile()
workflow.add_edge(START, "router")