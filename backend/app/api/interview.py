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
    instructions = f"""당신은 한국의 10년차 시니어 개발자이자 꼼꼼한 면접관입니다.
지원자의 프로필:
- 직무: {request.job_title}
- 분야: {request.field}
- 경력: {request.experience}
- 전공여부: {request.major}

당신의 임무:
1. 먼저 지원자에게 짧게 인사를 건네고 첫 질문을 던지세요.
2. 지원자의 프로필과 답변에 맞춰 날카로운 실무 위주의 꼬리 질문을 던지세요.
3. 한 번에 너무 많은 질문을 하지 말고, 한 번에 하나의 핵심만 물어보세요.
4. 반드시 자연스러운 한국어로 대답하세요.
"""

    # 3. OpenAI 서버에 세션 생성 요청 (토큰 발급)
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o-realtime-preview-2024-12-17",
        "modalities": ["audio", "text"],
        "instructions": instructions,
        "voice": "sage",  # 목소리 설정 (alloy, ash, ballad, coral, echo, sage, shimmer, verse)
        "tools": [
            {
                "type": "function",
                "name": "search_job_postings",
                "description": "지원자의 직무나 기술 스택과 관련된 한국 최신 채용 공고, 우대 조건, 요구 기술을 실시간으로 웹에서 검색합니다. 이 정보를 바탕으로 실무에서 실제로 묻는 깊이 있는 꼬리 질문을 만드세요.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "검색할 채용 키워드 (예: '프론트엔드 신입 채용 우대조건', 'Next.js 개발자 요구사항')"
                        }
                    },
                    "required": ["query"]
                }
            }
        ],
        "tool_choice": "auto",
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
