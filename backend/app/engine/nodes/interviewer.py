from app.engine.graphs.state import InterviewState

def interviewer_node(state: InterviewState):
    """
    면접관 AI 노드: 
    사용자의 프로필과 이전 답변 내역을 분석하여 다음 '꼬리 질문'을 생성합니다.
    """
    print(f"[Interviewer] {state.get('user_id', 'Unknown')}님의 답변을 바탕으로 다음 질문 생성 중...")
    
    # TODO: LangChain 프롬프트 템플릿(Persona 적용) 작성 및 LLM 호출
    
    return state
