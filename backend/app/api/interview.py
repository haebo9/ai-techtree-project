from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path
from typing import Dict, Any, List
from app.schemas_api.email import SendEmailRequest
from app.schemas_api.interview import (
    StartInterviewRequest, 
    StartInterviewResponse, 
    EndInterviewRequest,
    EndInterviewResponse
)

import uuid
import requests
import resend
import html
from datetime import datetime, timezone
from app.core.config import settings
from app.core.logger import get_logger
from app.services.invite_service import require_invite_session
from app.services.reflection_service import safe_generate_and_store_reflections
from app.services.interview_manager import (
    INTERVIEW_MODE_GUIDANCE,
    VOICE_INTERVIEWER_NAMES,
    build_manager_context,
    dedupe_tool_traces,
    normalize_job_list,
    normalize_tool_traces,
)

from app.engine.graphs.graph import get_interview_workflow
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter(dependencies=[Depends(require_invite_session)])

interview_workflow = get_interview_workflow()
logger = get_logger(__name__)

temp_sessions: Dict[str, Any] = {}

def _normalize_job_list(raw_jobs: Any, *, require_active: bool = False) -> List[Dict[str, str]]:
    return normalize_job_list(raw_jobs, require_active=require_active)


def _normalize_tool_traces(raw_traces: Any) -> List[Dict[str, Any]]:
    return normalize_tool_traces(raw_traces)


def _dedupe_tool_traces(raw_traces: Any) -> List[Dict[str, Any]]:
    return dedupe_tool_traces(raw_traces)


def prepare_interview_context(request: StartInterviewRequest) -> Dict[str, Any]:
    return build_manager_context({
        "user_id": request.user_id,
        "report_email": str(request.report_email),
        "job_title": request.job_title,
        "education": request.education,
        "experience": request.experience,
        "resume": request.resume,
        "raw_job_description": request.job_description or "",
        "job_image": request.job_image,
        "interview_mode": request.interview_mode,
        "messages": [],
        "status": "PREPARING",
    })

@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(request: StartInterviewRequest):
    """
    지원자의 프로필을 받아 새로운 면접 세션을 생성하고, 
    LangGraph manager로 면접 컨텍스트를 준비한 뒤 OpenAI Realtime API 연동 토큰을 발급합니다.
    """
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}
    initial_state = {
        "user_id": request.user_id,
        "report_email": str(request.report_email),
        "job_title": request.job_title,
        "field": "",
        "experience": request.experience,
        "education": request.education,
        "resume": request.resume,
        "major": "",
        "raw_job_description": request.job_description or "",
        "job_description": request.job_description or "",
        "job_image": request.job_image,
        "interview_mode": request.interview_mode,
        "messages": [],
        "saved_jobs": [],
        "tool_traces": [],
        "candidate_summary": "",
        "interview_brief": "",
        "status": "PREPARING",
    }
    context = interview_workflow.invoke(initial_state, config=config)

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-realtime-mini-2025-12-15",
        "modalities": ["audio", "text"],
        "instructions": context["realtime_instructions"],
        "voice": context["selected_voice"],
        "input_audio_transcription": {"model": "whisper-1"},
        "turn_detection": None,
    }
    
    try:
        response = requests.post("https://api.openai.com/v1/realtime/sessions", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        ephemeral_token = response.json()["client_secret"]["value"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI Session Error: {str(e)}")

    temp_sessions[session_id] = {
        "user_id": request.user_id,
        "report_email": str(request.report_email),
        "status": "IN_PROGRESS",
        "voice": context["selected_voice"],
        "interviewer_name": context["interviewer_name"],
        "job_title": context["job_title"],
        "experience": context["experience"],
        "education": context["education"],
        "resume": context["resume"],
        "job_description": context["job_description"],
        "job_posting_analysis": context["job_posting_analysis"],
        "job_posting_analysis_status": context["job_posting_analysis_status"],
        "interview_mode": context["interview_mode"],
        "prompt_variant": context["prompt_variant"],
        "guideline_selection": context["guideline_selection"],
        "reflection_source_ids": context["guideline_selection"].get("reflection_ids", []),
        "policy_source_ids": context["guideline_selection"].get("policy_ids", []),
        "prepared_jobs": context["prepared_jobs"],
        "context_jobs": context["context_jobs"],
        "tool_traces": [],
    }
    
    return StartInterviewResponse(
        session_id=session_id,
        ephemeral_token=ephemeral_token,
        message="면접 세션이 준비되었습니다.",
        job_posting_analysis=context["job_posting_analysis"],
        interview_mode=context["interview_mode"],
        prompt_variant=context["prompt_variant"],
        guideline_selection=context["guideline_selection"],
    )

@router.post("/{session_id}/end", response_model=EndInterviewResponse)
async def end_interview(
    background_tasks: BackgroundTasks,
    request: EndInterviewRequest,
    session_id: str = Path(..., description="면접 세션 ID")
):
    """
    면접을 종료하고 리포트 생성/이메일 발송은 백그라운드에서 처리합니다.
    """
    lc_messages = []
    for t in request.transcripts:
        if t.role == "user":
            lc_messages.append(HumanMessage(content=t.text))
        elif t.role == "ai":
            lc_messages.append(AIMessage(content=t.text))


    session_tool_traces = _normalize_tool_traces(temp_sessions.get(session_id, {}).get("tool_traces", []))
    request_tool_traces = _normalize_tool_traces(request.tool_traces)
    tool_traces = _dedupe_tool_traces(session_tool_traces + request_tool_traces)

    temp_sessions.setdefault(session_id, {})["status"] = "REPORT_QUEUED"
    background_tasks.add_task(
        generate_report_and_send_email,
        session_id=session_id,
        lc_messages=lc_messages,
        tool_traces=tool_traces,
        transcripts=[item.model_dump() for item in request.transcripts],
        interview_date=request.interview_date,
        interview_duration=request.interview_duration,
    )

    return EndInterviewResponse(
        session_id=session_id,
        status="queued",
        message="면접이 종료되었습니다. 리포트는 입력하신 이메일로 전송됩니다.",
    )

def generate_report_and_send_email(
    *,
    session_id: str,
    lc_messages: List[Any],
    tool_traces: List[Dict[str, Any]],
    transcripts: List[Dict[str, str]],
    interview_date: str | None,
    interview_duration: str | None,
) -> None:
    session = temp_sessions.get(session_id, {})
    config = {"configurable": {"thread_id": session_id}}

    try:
        temp_sessions.setdefault(session_id, {})["status"] = "REPORT_GENERATING"
        interview_workflow.update_state(config, {
            "status": "EVALUATING",
            "messages": lc_messages,
            "tool_traces": tool_traces,
        })

        final_state = interview_workflow.invoke(None, config=config)
        evaluation = final_state.get("evaluation_result", {})

        email_request = SendEmailRequest(
            email=session.get("report_email", ""),
            score=evaluation.get("score", 0),
            strengths=evaluation.get("strengths", []),
            weaknesses=evaluation.get("weaknesses", []),
            qa_review=evaluation.get("qa_review", []),
            communication_feedback=evaluation.get("communication_feedback", {}),
            self_intro_feedback=evaluation.get("self_intro_feedback", {}),
            role_fit=evaluation.get("role_fit", {}),
            tool_traces=tool_traces,
            transcripts=transcripts,
            interview_date=interview_date,
            interview_duration=interview_duration,
        )
        _send_report_email(email_request)

        safe_generate_and_store_reflections(
            session_id=session_id,
            job_title=final_state.get("job_title", session.get("job_title", "")),
            experience=final_state.get("experience", session.get("experience", "")),
            education=final_state.get("education", session.get("education", "")),
            messages=final_state.get("messages", lc_messages),
            evaluation=evaluation,
            interview_mode=final_state.get("interview_mode", session.get("interview_mode", "long")),
            injected_reflection_ids=final_state.get("reflection_source_ids", session.get("reflection_source_ids", [])),
            injected_policy_ids=final_state.get("policy_source_ids", session.get("policy_source_ids", [])),
        )

        temp_sessions.setdefault(session_id, {})["status"] = "REPORT_SENT"
        temp_sessions[session_id]["email_sent_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        logger.warning("Async report generation failed for session %s: %s", session_id, exc)
        temp_sessions.setdefault(session_id, {})["status"] = "REPORT_FAILED"
        temp_sessions[session_id]["error"] = str(exc)
    finally:
        _cleanup_completed_session(session_id)


def _cleanup_completed_session(session_id: str) -> None:
    session = temp_sessions.get(session_id)
    if not session:
        return

    for key in (
        "resume",
        "job_description",
        "job_posting_analysis",
        "context_jobs",
        "prepared_jobs",
        "report_email",
    ):
        session.pop(key, None)
    session["completed_at"] = datetime.now(timezone.utc).isoformat()


def _html(value: Any) -> str:
    return html.escape(str(value or ""))


def _html_multiline(value: Any) -> str:
    return _html(value).replace("\n", "<br/>")


def _has_feedback_content(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    for item in value.values():
        if isinstance(item, list) and item:
            return True
        if isinstance(item, (str, int, float)) and str(item).strip():
            return True
    return False


def _render_email_list(items: Any) -> str:
    if not isinstance(items, list) or not items:
        return '<p style="color: #64748b; font-size: 14px; margin: 0;">제공된 항목이 없습니다.</p>'
    return '<ul class="item-list">' + "".join(f"<li>{_html(item)}</li>" for item in items) + "</ul>"


def _role_fit_percent(role_fit: Dict[str, Any]) -> int:
    try:
        return max(0, min(100, int(role_fit.get("score", 0))))
    except (TypeError, ValueError):
        return 0


def _render_email_transcripts(transcripts: Any) -> str:
    if not isinstance(transcripts, list) or not transcripts:
        return '<p style="color: #64748b; font-size: 14px; margin: 0;">제공된 대화 내역이 없습니다.</p>'

    items = []
    for transcript in transcripts:
        if not isinstance(transcript, dict):
            continue
        role = transcript.get("role")
        is_ai = role == "ai"
        label = "면접관" if is_ai else "지원자"
        bubble_class = "transcript-ai" if is_ai else "transcript-user"
        items.append(f"""
                            <div class="transcript-row {bubble_class}">
                                <p class="transcript-label">{label}</p>
                                <p class="transcript-text">{_html_multiline(transcript.get('text', ''))}</p>
                            </div>
        """)
    return "".join(items)


def _render_extended_feedback_sections(request: SendEmailRequest) -> str:
    communication = request.communication_feedback or {}
    self_intro = request.self_intro_feedback or {}
    role_fit = request.role_fit or {}
    sections = []

    if _has_feedback_content(communication):
        sections.append(f"""
                    <div class="section">
                        <h3 class="section-title">🗣️ 말투/답변 습관 피드백</h3>
                        <p>{_html_multiline(communication.get('summary', ''))}</p>
                        <p><strong>좋았던 점</strong></p>
                        {_render_email_list(communication.get('strengths', []))}
                        <p><strong>개선할 습관</strong></p>
                        {_render_email_list(communication.get('habits_to_improve', []))}
                        <p><strong>다음 연습 액션</strong></p>
                        {_render_email_list(communication.get('action_items', []))}
                    </div>
        """)

    if _has_feedback_content(self_intro):
        sections.append(f"""
                    <div class="section">
                        <h3 class="section-title">👤 이력서 기반 자기소개 피드백</h3>
                        <p><strong>실제 자기소개 요약:</strong> {_html_multiline(self_intro.get('original_summary', ''))}</p>
                        <p><strong>개선 방향:</strong> {_html_multiline(self_intro.get('improvement_direction', ''))}</p>
                        <p><strong>보완할 점</strong></p>
                        {_render_email_list(self_intro.get('issues', []))}
                        <div class="script-box">
                            <p style="margin-top: 0;"><strong>추천 자기소개 멘트</strong></p>
                            <p style="margin-bottom: 0;">{_html_multiline(self_intro.get('improved_script', ''))}</p>
                        </div>
                        <p style="color: #64748b; font-size: 12px;">{_html_multiline(self_intro.get('evidence_note', ''))}</p>
                    </div>
        """)

    if _has_feedback_content(role_fit):
        role_fit_percent = _role_fit_percent(role_fit)
        sections.append(f"""
                    <div class="section">
                        <h3 class="section-title">📌 이력서-직무 적합도</h3>
                        <div class="fit-score">{role_fit_percent}%</div>
                        <p>{_html_multiline(role_fit.get('rationale', ''))}</p>
                        <p><strong>매칭 강점 키워드</strong></p>
                        {_render_email_list(role_fit.get('matched_keywords', []))}
                        <p><strong>보완 갭</strong></p>
                        {_render_email_list(role_fit.get('gaps', []))}
                    </div>
        """)

    return "".join(sections)


def _empty_job_recommendation_message(tool_traces: List[Dict[str, Any]]) -> str:
    statuses = {str(trace.get("status") or "") for trace in tool_traces if isinstance(trace, dict)}
    if "no_api_key" in statuses:
        return "채용 공고 검색 API 키가 설정되지 않아 추천 공고를 표시하지 못했습니다."
    if "search_error" in statuses:
        return "채용 공고 검색 중 오류가 발생해 추천 공고를 표시하지 못했습니다."
    if "filtered_expired" in statuses:
        return "검색 결과는 있었지만 마감되었거나 조건에 맞지 않는 공고가 제외되어 추천에 표시할 항목이 없습니다."
    if "no_results" in statuses:
        return "현재 조건에 맞는 채용 공고 검색 결과가 없어 추천에 표시할 항목이 없습니다."
    return "현재 맞춤 채용 공고를 찾지 못했습니다. 검색 결과가 없거나 마감된 것으로 확인된 공고만 있어 추천에 표시할 항목이 없습니다."


def _build_report_email_html(request: SendEmailRequest) -> str:
    extended_feedback_sections = _render_extended_feedback_sections(request)
    empty_job_message = _empty_job_recommendation_message(request.tool_traces)
    transcript_html = _render_email_transcripts(request.transcripts)

    return f"""
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
                .script-box {{ background-color: #eff6ff; border: 1px solid #bfdbfe; padding: 16px; border-radius: 8px; margin-top: 12px; }}
                .fit-score {{ font-size: 24px; font-weight: bold; color: #2563eb; margin-bottom: 8px; }}
                .transcript-wrap {{ background-color: #f8fafc; padding: 14px; border-radius: 10px; font-size: 14px; }}
                .transcript-row {{ padding: 12px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #e2e8f0; }}
                .transcript-ai {{ background-color: #eff6ff; border-color: #bfdbfe; }}
                .transcript-user {{ background-color: #f0fdf4; border-color: #bbf7d0; }}
                .transcript-label {{ margin: 0 0 6px 0; font-weight: bold; }}
                .transcript-ai .transcript-label {{ color: #1d4ed8; }}
                .transcript-user .transcript-label {{ color: #15803d; }}
                .transcript-text {{ margin: 0; color: #334155; }}
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

                    {extended_feedback_sections}

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
                            {f'<p style="margin: 6px 0 0 0; color: #64748b; font-size: 12px;">마감 여부 확인 필요</p>' if job.get('deadline_status') == 'unknown' else ''}
                        </div>
                        ''' for job in request.job_recommendations])}
                        {'''
                        <p style="color: #64748b; font-size: 14px; margin: 0;">
                            ''' + _html(empty_job_message) + '''
                        </p>
                        ''' if not request.job_recommendations else ''}
                    </div>

                    <div class="section">
                        <h3 class="section-title">🗣️ 전체 대화 내역</h3>
                        <div class="transcript-wrap">
                            {transcript_html}
                        </div>
                    </div>
                    
                </div>
            </div>
        </body>
    </html>
    """


def _send_report_email(request: SendEmailRequest):
    if not settings.RESEND_API_KEY:
        print(f"⚠️ RESEND_API_KEY 설정이 없습니다. 이메일 발송을 시뮬레이션합니다.\nTarget Email: {request.email}")
        return {"status": "success", "message": "Resend API 키가 없어 이메일 발송을 콘솔에 시뮬레이션했습니다."}

    resend.api_key = settings.RESEND_API_KEY
    html_content = _build_report_email_html(request)
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


@router.post("/{session_id}/email")
async def send_interview_email(session_id: str, request: SendEmailRequest):
    """
    면접 결과 리포트와 전체 대화 내역을 이메일로 전송합니다. (Resend API 사용)
    """
    return _send_report_email(request)
