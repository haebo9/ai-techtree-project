from app.engine.graphs.state import KeywordState

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