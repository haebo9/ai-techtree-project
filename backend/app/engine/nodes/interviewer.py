from app.engine.graphs.state import InterviewState
from app.engine.tools.job_search import search_korean_job_postings

def interviewer_node(state: InterviewState):
    """
    면접관 AI 노드 (에이전틱 흐름 적용): 
    필요 시 '채용 검색 도구(search_korean_job_postings)'를 사용하여
    실제 우대 조건이나 실무 트렌드를 바탕으로 날카로운 꼬리 질문을 생성합니다.
    """
    print(f"[Interviewer] {state.get('user_id', 'Unknown')}님의 면접 흐름을 분석 중입니다...")
    
    # TODO: 실제 LLM 연동 시 아래와 같이 툴을 바인딩하여 사용합니다.
    # llm_with_tools = llm.bind_tools([search_korean_job_postings])
    # response = llm_with_tools.invoke(state["messages"])
    
    return state
