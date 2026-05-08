from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from typing import Dict, Any
from app.schemas_api.interview import (
    StartInterviewRequest, 
    StartInterviewResponse, 
    ChatRequest, 
    ChatResponse, 
    EndInterviewRequest,
    EndInterviewResponse
)

router = APIRouter()

import uuid
import requests
from app.core.config import settings
from app.engine.prompts.api_interviewer import INTERVIEWER_SYSTEM_PROMPT

from app.engine.graphs.graph import interview_workflow
from langchain_core.messages import HumanMessage

temp_sessions: Dict[str, Any] = {}

@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(request: StartInterviewRequest):
    """
    지원자의 프로필을 받아 새로운 면접 세션을 생성하고, 
    OpenAI Realtime API 연동 토큰 발급 및 LangGraph 상태를 초기화합니다.
    """
    session_id = str(uuid.uuid4())
    
    # 1. 면접관 지침 준비
    instructions = INTERVIEWER_SYSTEM_PROMPT.format(
        job_title=request.job_title if request.job_title else "정보 없음",
        education=request.education if request.education else "정보 없음",
        experience=request.experience if request.experience else "정보 없음",
        resume=request.resume if request.resume else "정보 없음"
    )

    import random
    available_voices = ["alloy", "ash", "ballad", "coral", "echo", "sage", "shimmer", "verse"]
    selected_voice = random.choice(available_voices)

    # 2. OpenAI Realtime 세션 생성
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-realtime-mini-2025-12-15",
        "modalities": ["audio", "text"],
        "instructions": instructions,
        "voice": selected_voice,
        "tools": [
            {
                "type": "function",
                "name": "search_job_postings",
                "description": "지원자의 직무 관련 실시간 채용 정보를 검색합니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    }
                }
            }
        ],
        "tool_choice": "auto",
        "input_audio_transcription": {"model": "whisper-1"},
        "turn_detection": None,
    }
    
    try:
        response = requests.post("https://api.openai.com/v1/realtime/sessions", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        ephemeral_token = response.json()["client_secret"]["value"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI Session Error: {str(e)}")
    
    # 3. LangGraph 초기 상태 설정
    initial_state = {
        "user_id": request.user_id,
        "job_title": request.job_title,
        "field": "",  # request에 없음
        "experience": request.experience,
        "education": request.education,
        "resume": request.resume,
        "major": "",  # request에 없음
        "messages": [],
        "status": "IN_PROGRESS"
    }
    interview_workflow.update_state({"configurable": {"thread_id": session_id}}, initial_state)
    
    temp_sessions[session_id] = {"user_id": request.user_id, "status": "IN_PROGRESS"}
    
    return StartInterviewResponse(
        session_id=session_id,
        ephemeral_token=ephemeral_token,
        message="면접 세션이 준비되었습니다."
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
    LangGraph 워크플로우를 호출하여 AI 면접관의 다음 대화를 생성합니다.
    """
    config = {"configurable": {"thread_id": session_id}}
    input_state = {"messages": [HumanMessage(content=request.message)]}
    
    # 그래프 실행
    final_state = interview_workflow.invoke(input_state, config=config)
    
    # 마지막 AI 메시지 추출
    ai_reply = final_state["messages"][-1].content
    
    return ChatResponse(reply=ai_reply)

from langchain_core.messages import HumanMessage, AIMessage

@router.post("/{session_id}/end", response_model=EndInterviewResponse)
async def end_interview(
    request: EndInterviewRequest,
    session_id: str = Path(..., description="면접 세션 ID")
):
    """
    면접을 종료하고 프론트엔드에서 전달받은 대화 내역(transcripts)을 바탕으로 Evaluator 노드를 실행합니다.
    """
    config = {"configurable": {"thread_id": session_id}}
    
    # 1. 프론트엔드에서 받은 transcripts를 LangChain Message 객체로 변환
    lc_messages = []
    for t in request.transcripts:
        if t.role == "user":
            lc_messages.append(HumanMessage(content=t.text))
        elif t.role == "ai":
            lc_messages.append(AIMessage(content=t.text))
            
    # 2. 상태를 EVALUATING으로 변경하고 메시지 내역 덮어쓰기
    interview_workflow.update_state(config, {"status": "EVALUATING", "messages": lc_messages})
    
    # 그래프 실행 (Evaluator 노드까지 진행됨)
    final_state = interview_workflow.invoke(None, config=config)
    
    evaluation = final_state.get("evaluation_result", {})
    
    return EndInterviewResponse(
        session_id=session_id,
        score=evaluation.get("score", 0),
        strengths=evaluation.get("strengths", []),
        weaknesses=evaluation.get("weaknesses", []),
        job_recommendations=evaluation.get("job_recommendations", [])
    )
