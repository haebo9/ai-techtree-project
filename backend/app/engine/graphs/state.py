from typing import TypedDict, Annotated, Dict, Any, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class InterviewState(TypedDict):
    """
    AI 가상 면접을 위한 상태(State) 스키마입니다.
    """
    # 1. 지원자 프로필 정보 (면접 초기화 시 주입)
    user_id: str
    job_title: str       # 상세 직무 (예: React 프론트엔드 개발자)
    field: str           # 분야 (예: frontend, backend 등)
    experience: str      # 경력 (신입, 1~3년차 등)
    major: str           # 전공 여부
    
    # 2. 대화 기록 (LangGraph의 add_messages reducer를 통해 누적됨)
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 3. 면접 평가 결과 (면접 종료 시 Evaluator 노드에서 작성)
    evaluation_result: Optional[Dict[str, Any]]
    
    # 4. 진행 상태 제어 플래그
    status: str          # "IN_PROGRESS"(진행 중) -> "EVALUATING"(평가 중) -> "COMPLETED"(완료)
