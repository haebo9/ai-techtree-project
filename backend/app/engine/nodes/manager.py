from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from app.core.llm import get_llm
from app.engine.graphs.state import InterviewState
from app.services.interview_manager import build_manager_context
from app.engine.tools.job_search import search_korean_job_postings
import json

tools = [search_korean_job_postings]
manager_tool_node = ToolNode(tools)

def manager_agent_node(state: InterviewState):
    """
    LLM 매니저 노드.
    지원자의 직무 관련 정보가 부족할 경우 자율적으로 `search_korean_job_postings` 툴을 호출합니다.
    """
    llm = get_llm(temperature=0).bind_tools(tools)
    
    job_title = state.get("job_title", "정보 없음")
    job_description = state.get("job_description") or state.get("raw_job_description", "")
    
    system_prompt = f"""
    당신은 면접 준비 매니저입니다.
    
    - 지원 직무: {job_title}
    - 사용자가 제공한 채용 공고: {job_description}
    
    [도구 사용 규칙]
    - 사용자가 제공한 채용 공고 정보가 없거나, 직무 관련 필요 역량 및 우대 역량 등의 정보가 부족하면
      `search_korean_job_postings` 툴을 1회 호출하세요.
    검색 쿼리(query)는 '{job_title}' 직무명으로 설정하세요.
    - 정보가 이미 충분하다면 툴을 호출하지 말고 '정보가 충분하여 면접 준비를 완료합니다.'라고 답변하세요.
    - 직무명이 '정보 없음'이거나 공백이면 툴을 호출하지 말고 '지원 직무 정보가 부족하여 기본 면접 가이드로 진행합니다.'라고 답변하세요.
    """
    
    # We only want the agent to see the system prompt and any previous tool messages (if loop occurs)
    # We shouldn't use the full interview transcript if this runs before interview.
    # At this point, state["messages"] might only contain previous thoughts or be empty.
    messages = [SystemMessage(content=system_prompt)] + state.get("messages", [])
    
    response = llm.invoke(messages)
    
    return {"messages": [response]}

def manager_finalize_node(state: InterviewState):
    """
    매니저 최종 노드.
    툴 실행 결과를 바탕으로 Realtime 시스템 프롬프트를 조립합니다.
    """
    # Extract context jobs from tool messages if any
    context_jobs = []
    
    for message in reversed(state.get("messages", [])):
        if isinstance(message, ToolMessage):
            try:
                jobs = json.loads(message.content)
                if isinstance(jobs, list):
                    context_jobs.extend(jobs)
            except Exception:
                pass
            break
            
    # Update state with the extracted context_jobs so build_manager_context can use them
    state_dict = dict(state)
    if context_jobs:
        state_dict["context_jobs"] = context_jobs
        
    return build_manager_context(state_dict)
