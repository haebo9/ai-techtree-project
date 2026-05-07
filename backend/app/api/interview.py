from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# 요청(Request) 데이터 모델 스키마
class StartInterviewRequest(BaseModel):
    user_id: str
    job_title: str
    field: str
    experience: str
    major: str

class ChatRequest(BaseModel):
    message: str

# API 엔드포인트 뼈대
@router.post("/start")
async def start_interview(request: StartInterviewRequest):
    """
    면접 세션을 생성하고 AI 면접관의 첫 인사말(또는 첫 질문)을 반환합니다.
    """
    # TODO: DB에 세션 생성 -> LangGraph 초기화 -> 첫 응답 반환
    return {
        "message": "면접 세션이 생성되었습니다.", 
        "session_id": "session_12345",
        "reply": "안녕하세요. 지원해주셔서 감사합니다. 간단한 자기소개 부탁드립니다."
    }

@router.post("/{session_id}/chat")
async def chat(session_id: str, request: ChatRequest):
    """
    사용자의 답변을 받아 AI 면접관의 다음 질문(또는 리액션)을 반환합니다.
    """
    # TODO: LangGraph의 interviewer_node를 호출하여 다음 대화 흐름 진행 (Streaming 지원 예정)
    return {
        "reply": f"[{request.message}] 라고 답변하셨군요. 그렇다면 관련된 다음 질문을 드리겠습니다..."
    }

@router.post("/{session_id}/end")
async def end_interview(session_id: str):
    """
    면접을 강제로 종료하고 종합 평가 리포트 생성을 트리거합니다.
    """
    # TODO: LangGraph 상태를 'EVALUATING'으로 변경 후 evaluator_node 호출
    return {
        "message": "면접이 종료되었습니다. 평가 리포트 생성을 시작합니다."
    }
