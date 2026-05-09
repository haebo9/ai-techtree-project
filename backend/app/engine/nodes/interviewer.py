from app.engine.graphs.state import InterviewState
from app.engine.tools.job_search import search_korean_job_postings
from app.core.llm import get_llm
from app.engine.prompts.api_interview import INTERVIEWER_SYSTEM_PROMPT
from langchain_core.messages import SystemMessage

def _state_text(state: InterviewState, key: str, default: str = "정보 없음") -> str:
    value = str(state.get(key) or "").strip()
    return value if value else default

def interviewer_node(state: InterviewState):
    """
    면접관 AI 노드: 
    시스템 프롬프트와 현재 대화 내역을 결합하여 다음 질문이나 툴 호출을 생성합니다.
    """
    llm = get_llm()
    # 도구 바인딩 (에이전틱 루프를 위해 필요)
    llm_with_tools = llm.bind_tools([search_korean_job_postings])
    
    # 시스템 프롬프트 준비 (지원자 정보 주입)
    system_content = INTERVIEWER_SYSTEM_PROMPT.format(
        interviewer_name=_state_text(state, "interviewer_name", "Alex"),
        job_title=_state_text(state, "job_title"),
        education=_state_text(state, "education"),
        experience=_state_text(state, "experience"),
        resume=_state_text(state, "resume"),
        job_description=_state_text(state, "job_description", "맞춤형 채용 공고 정보 없음"),
        reflection_guidelines=str(state.get("reflection_guidelines") or "").strip()
    )
    
    messages = [SystemMessage(content=system_content)] + state["messages"]
    
    # LLM 호출
    response = llm_with_tools.invoke(messages)
    
    return {"messages": [response]}
