from app.engine.graphs.state import InterviewState

def evaluator_node(state: InterviewState):
    """
    평가자 AI 노드:
    면접이 종료된 후, 전체 대화 내역(`messages`)을 바탕으로 
    강점, 약점, 점수, 추천 채용 공고를 포함한 종합 리포트를 생성합니다.
    """
    print(f"[Evaluator] {state.get('user_id', 'Unknown')}님의 면접 종합 평가 리포트 생성 중...")
    
    # TODO: 전체 맥락 요약 프롬프트 작성 및 Pydantic Structured Output(JSON) 추출
    
    return state
