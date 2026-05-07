from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from typing import Dict, Any
from app.schemas_api.interview import (
    StartInterviewRequest, 
    StartInterviewResponse, 
    ChatRequest, 
    ChatResponse, 
    EndInterviewResponse
)

router = APIRouter()

import uuid
import requests
from app.core.config import settings

# 메모리용 임시 저장소 (추후 MongoDB / LangGraph Checkpointer로 대체)
temp_sessions: Dict[str, Any] = {}

@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(request: StartInterviewRequest):
    """
    지원자의 프로필을 받아 새로운 면접 세션을 생성하고, 
    OpenAI Realtime API(WebRTC) 연동을 위한 일회용 토큰(ephemeral token)을 발급받습니다.
    """
    # 1. 고유 세션 ID 생성
    session_id = str(uuid.uuid4())
    
    # 2. 면접관 페르소나 및 사용자 정보 세팅 (OpenAI 시스템 프롬프트)
    instructions = f"""당신은 10년차 시니어이자 꼼꼼하고 엄격한 면접관입니다.
        지원자의 프로필:
        - 지원 직무: {request.job_title}
        - 학력: {request.education}
        - 경력: {request.experience}
        - 이력/자기소개 요약: {request.resume}

        당신의 핵심 임무:
        1. 먼저 지원자에게 짧게 인사를 건네고 첫 질문을 던지세요.
        2. 'search_job_postings' 도구를 사용하여 반드시 지원자의 '직무', '학력', '경력'이 모두 포함된 구체적인 키워드로 실제 채용 시장의 우대조건이나 필요 역량을 검색하세요. (예: '{request.job_title} {request.experience} {request.education} 채용 우대조건')
        3. [중요] 검색한 채용 정보를 지원자에게 요약해주거나 설명해주지 마세요. 당신은 정보 제공 봇이 아니라 '면접관'입니다.
        4. 검색된 실제 시장의 요구사항을 바탕으로, 지원자가 해당 업무를 제대로 수행할 수 있는지 검증하는 매우 날카롭고 실무적인 꼬리 질문을 던지세요.
        5. 한 번에 하나의 핵심만 묻고, 지원자의 대답을 들은 후 다시 파고드는 질문을 하세요.
        6. 반드시 자연스럽고 권위있는 한국어로 대답하세요.
        """

    # 3. OpenAI 서버에 세션 생성 요청 (토큰 발급)
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-realtime-mini-2025-12-15",
        "modalities": ["audio", "text"],
        "instructions": instructions,
        "voice": "sage",
        "tools": [
            {
                "type": "function",
                "name": "search_job_postings",
                "description": "지원자의 직무, 학력, 경력, 이력과 관련된 한국 최신 채용 공고와 우대 조건을 실시간으로 검색합니다. 이 정보를 바탕으로 지원자에게 던질 날카로운 실무 면접 질문을 구상하세요.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "검색할 채용 키워드 (예: '프로덕트 매니저 3년차 학사 우대조건', '데이터 애널리스트 신입 석사 요구역량')"
                        }
                    },
                    "required": ["query"]
                }
            }
        ],
        "tool_choice": "auto",
        "input_audio_transcription": {
            "model": "whisper-1"
        },
        "turn_detection": None,  # 수동 응답(Push-To-Talk)을 위해 VAD 비활성화
    }
    
    # 동기식 요청 (추후 httpx를 활용한 비동기로 고도화 권장)
    try:
        response = requests.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        ephemeral_token = data["client_secret"]["value"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI Session Error: {str(e)}")
    
    # 4. 임시 세션 저장
    temp_sessions[session_id] = {
        "user_id": request.user_id,
        "status": "IN_PROGRESS"
    }
    
    # 5. 토큰 반환
    return StartInterviewResponse(
        session_id=session_id,
        ephemeral_token=ephemeral_token,
        message="면접 세션이 준비되었습니다. 연결을 시도합니다..."
    )

class ToolSearchRequest(BaseModel):
    query: str

@router.post("/tools/search_job")
async def execute_search_job(request: ToolSearchRequest):
    """
    프론트엔드 WebRTC에서 OpenAI Realtime API가 툴 호출을 요청했을 때,
    실제 검색 툴을 실행하고 결과를 반환하는 엔드포인트입니다.
    """
    from app.engine.tools.job_search import search_korean_job_postings
    
    # LangChain @tool 데코레이터가 붙은 함수는 .invoke()로 실행
    result = search_korean_job_postings.invoke({"query": request.query})
    return {"result": result}

@router.post("/{session_id}/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session_id: str = Path(..., description="면접 세션 ID")
):
    """
    사용자의 답변을 받아 AI 면접관의 다음 질문(꼬리 질문)을 반환합니다.
    """
    if session_id not in temp_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if temp_sessions[session_id]["status"] != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail="Interview is already completed.")

    user_message = request.message
    
    # TODO: LangGraph의 interviewer_node 호출 
    # (session_id를 thread_id로 사용하여 이전 대화 문맥(Memory) 불러오기)
    
    ai_reply = f"[{user_message}] 라고 답변하셨군요. 그렇다면 이와 관련된 다음 질문을 드리겠습니다..."
    
    return ChatResponse(reply=ai_reply)

@router.post("/{session_id}/end", response_model=EndInterviewResponse)
async def end_interview(session_id: str = Path(..., description="면접 세션 ID")):
    """
    면접을 강제로 종료하고, 지금까지의 대화를 분석해 종합 평가 리포트를 생성합니다.
    """
    if session_id not in temp_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # 상태 업데이트
    temp_sessions[session_id]["status"] = "EVALUATING"
    
    # TODO: LangGraph 상태를 EVALUATING으로 변경 후 evaluator_node 호출
    # 결과 JSON 파싱
    
    temp_sessions[session_id]["status"] = "COMPLETED"
    
    return EndInterviewResponse(
        session_id=session_id,
        score=85,
        strengths=["상태 관리 도구의 차이점을 명확히 인지함", "논리적인 답변 구조"],
        weaknesses=["SSR 환경에서의 최적화 경험 부족"],
        job_recommendations=[
            {"company": "토스", "title": "Frontend Developer (React)"},
            {"company": "카카오", "title": "웹 프론트엔드 개발자"}
        ]
    )
