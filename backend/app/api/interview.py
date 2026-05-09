from fastapi import APIRouter, BackgroundTasks, HTTPException, Path
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
import random
import requests
from app.core.config import settings
from app.core.logger import get_logger
from app.engine.prompts.api_interview import INTERVIEWER_SYSTEM_PROMPT
from app.services.reflection_service import ReflectionService, safe_generate_and_store_reflections

from app.engine.graphs.graph import get_interview_workflow
from langchain_core.messages import HumanMessage, AIMessage

interview_workflow = get_interview_workflow()
logger = get_logger(__name__)

temp_sessions: Dict[str, Any] = {}

VOICE_INTERVIEWER_NAMES: Dict[str, str] = {
    "alloy": "Alex",
    "ash": "Noah",
    "ballad": "Ethan",
    "coral": "Sophia",
    "echo": "Daniel",
    "sage": "Mina",
    "shimmer": "Yuna",
    "verse": "Jin",
}

def _prompt_value(value: str | None, default: str = "정보 없음") -> str:
    cleaned = (value or "").strip()
    return cleaned if cleaned else default

@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(request: StartInterviewRequest):
    """
    지원자의 프로필을 받아 새로운 면접 세션을 생성하고, 
    OpenAI Realtime API 연동 토큰 발급 및 LangGraph 상태를 초기화합니다.
    """
    session_id = str(uuid.uuid4())
    job_title = _prompt_value(request.job_title)
    education = _prompt_value(request.education)
    experience = _prompt_value(request.experience)
    resume = _prompt_value(request.resume)
    
    if request.job_description and request.job_description.strip():
        job_desc = request.job_description.strip()
    elif request.job_image:
        job_desc = "[사용자가 이미지(캡처본) 형태로 채용 공고를 직접 제공했습니다.]"
    else:
        job_desc = "맞춤형 채용 공고 정보 없음"

    try:
        reflection_guidelines = ReflectionService().get_prompt_guidelines(
            job_title=job_title,
            experience=experience,
            education=education,
            limit=5,
        )
    except Exception as e:
        logger.warning("Reflection guideline lookup failed: %s", e)
        reflection_guidelines = ""

    selected_voice = random.choice(list(VOICE_INTERVIEWER_NAMES.keys()))
    interviewer_name = VOICE_INTERVIEWER_NAMES[selected_voice]
    
    # 1. 면접관 지침 준비
    instructions = INTERVIEWER_SYSTEM_PROMPT.format(
        interviewer_name=interviewer_name,
        job_title=job_title,
        education=education,
        experience=experience,
        resume=resume,
        job_description=job_desc,
        reflection_guidelines=reflection_guidelines
    )

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
        "job_title": job_title,
        "field": "",  # request에 없음
        "experience": experience,
        "education": education,
        "resume": resume,
        "job_description": job_desc,
        "reflection_guidelines": reflection_guidelines,
        "interviewer_name": interviewer_name,
        "major": "",  # request에 없음
        "messages": [],
        "saved_jobs": [],
        "status": "IN_PROGRESS"
    }
    interview_workflow.update_state({"configurable": {"thread_id": session_id}}, initial_state)
    
    temp_sessions[session_id] = {
        "user_id": request.user_id,
        "status": "IN_PROGRESS",
        "voice": selected_voice,
        "interviewer_name": interviewer_name,
    }
    
    return StartInterviewResponse(
        session_id=session_id,
        ephemeral_token=ephemeral_token,
        message="면접 세션이 준비되었습니다."
    )

class ToolSearchRequest(BaseModel):
    query: str
    experience: str = ""
    education: str = ""

@router.post("/tools/search_job")
async def execute_search_job(request: ToolSearchRequest):
    """
    프론트엔드 WebRTC에서 OpenAI Realtime API가 툴 호출을 요청했을 때,
    실제 검색 툴을 실행하고 결과를 반환하는 엔드포인트입니다.
    """
    from app.engine.tools.job_search import search_korean_job_postings
    
    # LangChain @tool 데코레이터가 붙은 함수는 .invoke()로 실행
    result = search_korean_job_postings.invoke({
        "query": request.query,
        "experience": request.experience,
        "education": request.education
    })
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
    background_tasks: BackgroundTasks,
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
            
    # 2. 상태를 EVALUATING으로 변경하고 메시지 내역 덮어쓰기 및 검색된 일자리 저장
    interview_workflow.update_state(config, {
        "status": "EVALUATING", 
        "messages": lc_messages,
        "saved_jobs": request.saved_jobs
    })
    
    # 그래프 실행 (Evaluator 노드까지 진행됨)
    final_state = interview_workflow.invoke(None, config=config)
    
    evaluation = final_state.get("evaluation_result", {})
    background_tasks.add_task(
        safe_generate_and_store_reflections,
        session_id=session_id,
        job_title=final_state.get("job_title", ""),
        experience=final_state.get("experience", ""),
        education=final_state.get("education", ""),
        messages=final_state.get("messages", lc_messages),
        evaluation=evaluation,
        saved_jobs=evaluation.get("job_recommendations") or request.saved_jobs,
    )
    
    return EndInterviewResponse(
        session_id=session_id,
        score=evaluation.get("score", 0),
        strengths=evaluation.get("strengths", []),
        weaknesses=evaluation.get("weaknesses", []),
        qa_review=evaluation.get("qa_review", []),
        job_recommendations=evaluation.get("job_recommendations", [])
    )

from app.schemas_api.email import SendEmailRequest
import resend

@router.post("/{session_id}/email")
async def send_interview_email(session_id: str, request: SendEmailRequest):
    """
    면접 결과 리포트와 전체 대화 내역을 이메일로 전송합니다. (Resend API 사용)
    """
    if not settings.RESEND_API_KEY:
        print(f"⚠️ RESEND_API_KEY 설정이 없습니다. 이메일 발송을 시뮬레이션합니다.\nTarget Email: {request.email}")
        return {"status": "success", "message": "Resend API 키가 없어 이메일 발송을 콘솔에 시뮬레이션했습니다."}

    resend.api_key = settings.RESEND_API_KEY

    # 이메일 내용 구성 (HTML)
    html_content = f"""
    <html>
        <head>
            <style>
                body {{ font-family: 'Apple SD Gothic Neo', sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2563eb; color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px; }}
                .section {{ margin-bottom: 24px; }}
                .section-title {{ color: #1e40af; border-bottom: 2px solid #bfdbfe; padding-bottom: 8px; margin-bottom: 16px; }}
                .score {{ font-size: 32px; font-weight: bold; color: #2563eb; text-align: center; }}
                .item-list {{ margin: 0; padding-left: 20px; }}
                .qa-box {{ background-color: #f8fafc; padding: 15px; border-radius: 8px; margin-bottom: 12px; }}
                .job-box {{ border: 1px solid #e2e8f0; padding: 12px; border-radius: 8px; margin-bottom: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>면접 종합 평가 리포트</h2>
                </div>
                <div class="content">
                    <div style="text-align: right; font-size: 12px; color: #666; margin-bottom: 10px;">
                        {f'일시: {request.interview_date}' if request.interview_date else ''}<br/>
                        {f'소요 시간: {request.interview_duration}' if request.interview_duration else ''}
                    </div>
                    <div class="section">
                        <div class="score">{request.score} / 100 점</div>
                    </div>
                    
                    <div class="section">
                        <h3 class="section-title">✅ 강점 (Strengths)</h3>
                        <ul class="item-list">
                            {"".join([f"<li>{s}</li>" for s in request.strengths])}
                        </ul>
                    </div>

                    <div class="section">
                        <h3 class="section-title">🚀 개선점 (Areas for Improvement)</h3>
                        <ul class="item-list">
                            {"".join([f"<li>{w}</li>" for w in request.weaknesses])}
                        </ul>
                    </div>

                    <div class="section">
                        <h3 class="section-title">📝 상세 답변 분석</h3>
                        {"".join([f'''
                        <div class="qa-box">
                            <p><strong>Q.</strong> {qa.get('question', '')}</p>
                            <p><strong>A.</strong> {qa.get('answer', '')}</p>
                            <p style="color: #2563eb;"><strong>AI 코멘트:</strong> {qa.get('feedback', '')}</p>
                        </div>
                        ''' for qa in request.qa_review])}
                    </div>

                    <div class="section">
                        <h3 class="section-title">🎯 맞춤 채용 공고</h3>
                        {"".join([f'''
                        <div class="job-box">
                            <p style="color: #2563eb; font-weight: bold; margin: 0 0 4px 0;">{job.get('company', '')}</p>
                            <p style="margin: 0; font-weight: bold;">
                                <a href="{job.get('url', '#')}" style="color: #333; text-decoration: none;">{job.get('title', '')}</a>
                            </p>
                        </div>
                        ''' for job in request.job_recommendations])}
                    </div>
                    
                    <div class="section">
                        <h3 class="section-title">🗣️ 전체 대화 내역</h3>
                        <div style="background-color: #f1f5f9; padding: 15px; border-radius: 8px; font-size: 14px;">
                            {"".join([f'''
                            <p style="margin-bottom: 12px;">
                                <strong>{'면접관' if t.get('role') == 'ai' else '지원자'}:</strong><br/>
                                {t.get('text', '')}
                            </p>
                            ''' for t in request.transcripts])}
                        </div>
                    </div>
                    
                </div>
            </div>
        </body>
    </html>
    """

    params = {
        "from": "TechTree <no-reply@haebo.pro>",
        "to": [request.email],
        "subject": "TechTree 가상 면접 종합 평가 리포트",
        "html": html_content,
    }

    try:
        resend.Emails.send(params)
        return {"status": "success", "message": "이메일이 성공적으로 전송되었습니다."}
    except Exception as e:
        print(f"❌ Resend 이메일 전송 실패: {e}")
        raise HTTPException(status_code=500, detail="이메일 전송에 실패했습니다.")
