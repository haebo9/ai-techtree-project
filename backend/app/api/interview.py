from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path
from pydantic import BaseModel
from typing import Dict, Any, List
from app.schemas_api.email import SendEmailRequest
from app.schemas_api.interview import (
    StartInterviewRequest, 
    StartInterviewResponse, 
    ChatRequest, 
    ChatResponse, 
    EndInterviewRequest,
    EndInterviewResponse
)

import uuid
import random
import requests
import resend
import html
from langchain_openai import ChatOpenAI
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from app.core.config import settings
from app.core.logger import get_logger
from app.engine.prompts.api_interview import build_realtime_interviewer_prompt, normalize_interview_mode
from app.services.invite_service import require_invite_session
from app.services.reflection_service import ReflectionService, safe_generate_and_store_reflections

from app.engine.graphs.graph import get_interview_workflow
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter(dependencies=[Depends(require_invite_session)])

interview_workflow = get_interview_workflow()
logger = get_logger(__name__)

temp_sessions: Dict[str, Any] = {}
JOB_SEARCH_TIMEOUT_SECONDS = 10
JOB_IMAGE_PLACEHOLDER = "[사용자가 이미지(캡처본) 형태로 채용 공고를 직접 제공했습니다.]"

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

INTERVIEW_MODE_GUIDANCE: Dict[str, Dict[str, str]] = {
    "short": {
        "label": "짧은 면접",
        "guidance": (
            "목표 시간은 약 7분입니다. 너무 길게 끌지 말고, "
            "아이스브레이킹 후 자기소개/지원동기를 확인한 다음 대표 경험 1개만 다루세요. "
            "핵심 직무 질문은 최대 3개, 꼬리 질문은 전체 면접에서 최대 1회만 사용하세요. "
            "대표 경험에 대해 성과, 사용 도구, 팀 피드백 중 하나를 확인했다면 같은 경험에 대한 추가 세부 질문은 하지 말고 마무리로 전환하세요. "
            "'마지막으로', '마무리로'라고 말한 뒤 지원자가 답변하면 새 질문을 하지 말고 종료 멘트만 하세요. "
            "평가 근거가 어느 정도 확보되면 추가 탐색보다 마지막 발언 기회를 주고 명확한 종료 멘트로 마무리하세요."
        ),
    },
    "long": {
        "label": "긴 면접",
        "guidance": (
            "목표 시간은 약 20분입니다. 아이스브레이킹과 자기소개/지원동기 이후, "
            "이력서 기반 대표 프로젝트 1-2개, 채용 공고 요건 기반 직무 질문, 협업/문제 해결, 실패·개선 경험까지 균형 있게 진행하세요. "
            "충분한 평가 근거가 확보되면 명확한 종료 멘트로 마무리하세요."
        ),
    },
}

def _prompt_value(value: str | None, default: str = "정보 없음") -> str:
    cleaned = (value or "").strip()
    return cleaned if cleaned else default

def _interview_mode_settings(mode: str | None) -> Dict[str, str]:
    normalized = normalize_interview_mode(mode)
    return INTERVIEW_MODE_GUIDANCE.get(normalized, INTERVIEW_MODE_GUIDANCE["long"])

def _normalize_job_list(raw_jobs: Any, *, require_active: bool = False) -> List[Dict[str, str]]:
    from app.engine.tools.job_search import classify_job_deadline_status, is_recommendable_active_job

    if not isinstance(raw_jobs, list):
        return []

    jobs = []
    seen_keys = set()
    for job in raw_jobs:
        if not isinstance(job, dict):
            continue
        normalized = {
            "company": str(job.get("company") or "회사명 미상"),
            "title": str(job.get("title") or "공고명 미상"),
            "url": str(job.get("url") or ""),
            "content": str(job.get("content") or ""),
        }
        url = normalized["url"]
        dedupe_key = (
            url.strip().lower() if url else "",
            normalized["company"].strip().lower(),
            normalized["title"].strip().lower(),
        )
        fallback_key = ("", normalized["company"].strip().lower(), normalized["title"].strip().lower())
        if dedupe_key in seen_keys or fallback_key in seen_keys:
            continue
        if require_active and not is_recommendable_active_job(normalized):
            continue
        if require_active:
            normalized["deadline_status"] = classify_job_deadline_status(normalized)
        seen_keys.add(dedupe_key)
        seen_keys.add(fallback_key)
        jobs.append(normalized)
    return jobs[:3]

def _normalize_tool_traces(raw_traces: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_traces, list):
        return []
    return [trace for trace in raw_traces if isinstance(trace, dict)]

def _dedupe_tool_traces(raw_traces: Any) -> List[Dict[str, Any]]:
    deduped = []
    seen = set()
    for trace in _normalize_tool_traces(raw_traces):
        key = (
            str(trace.get("tool_name") or ""),
            str(trace.get("query") or ""),
            str(trace.get("status") or ""),
            str(trace.get("reason") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(trace)
    return deduped

def _analyze_job_image_for_context(image: str | None) -> Dict[str, Any]:
    if not image:
        return {
            "status": "not_provided",
            "summary": "",
        }

    image_url = image if image.startswith("data:image") else f"data:image/jpeg;base64,{image}"
    try:
        llm = ChatOpenAI(
            model="gpt-5.4-nano",
            openai_api_key=settings.OPENAI_API_KEY,
            max_completion_tokens=900,
        )
        response = llm.invoke([
            HumanMessage(content=[
                {
                    "type": "text",
                    "text": (
                        "이 이미지는 채용 공고 캡처입니다. 최종 리포트와 면접 질문에 사용할 수 있도록 "
                        "회사명, 직무명, 주요업무, 자격요건, 우대사항, 기술스택, 채용조건을 한국어로 간결하게 구조화해 주세요. "
                        "이미지에서 확인되지 않는 항목은 '확인 불가'라고 쓰세요."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
            ])
        ])
        summary = str(response.content or "").strip()
        if not summary:
            raise ValueError("empty image analysis result")
        return {
            "status": "image_analyzed",
            "summary": summary,
        }
    except Exception as exc:
        logger.warning("Job posting image analysis failed: %s", exc)
        return {
            "status": "image_analysis_failed",
            "summary": JOB_IMAGE_PLACEHOLDER,
            "error": str(exc),
        }

def _prepare_job_materials(job_title: str, experience: str, education: str) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    from app.engine.tools.job_search import search_korean_job_postings

    if not settings.TAVILY_API_KEY:
        logger.warning("Skipping prepared job search because TAVILY_API_KEY is not configured.")
        return [], []

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        search_korean_job_postings.invoke,
        {
            "query": f"{job_title} 채용",
            "experience": experience,
            "education": education,
        },
    )
    try:
        result = future.result(timeout=JOB_SEARCH_TIMEOUT_SECONDS)
    except FutureTimeoutError:
        future.cancel()
        logger.warning("Prepared job search timed out after %s seconds for %s", JOB_SEARCH_TIMEOUT_SECONDS, job_title)
        return [], []
    except Exception as exc:
        logger.warning("Prepared job search failed for %s: %s", job_title, exc)
        return [], []
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    context_jobs = _normalize_job_list(result)
    recommended_jobs = _normalize_job_list(result, require_active=True)
    return context_jobs, recommended_jobs

def _format_prepared_job_context(job_desc: str, prepared_jobs: List[Dict[str, str]]) -> str:
    sections = []
    if job_desc and job_desc != "맞춤형 채용 공고 정보 없음":
        sections.append(f"[사용자가 제공한 지원 공고]\n{job_desc}")
    elif job_desc:
        sections.append(job_desc)

    if prepared_jobs:
        job_lines = []
        for index, job in enumerate(prepared_jobs, start=1):
            content = str(job.get("content") or "").strip()
            if len(content) > 500:
                content = content[:500].rstrip() + "..."
            job_lines.append(
                f"{index}. {job.get('company', '회사명 미상')} - {job.get('title', '공고명 미상')}\n"
                f"   URL: {job.get('url', '')}\n"
                f"   요약: {content or '상세 요약 없음'}"
            )
        sections.append("[면접 시작 전 선별한 모집중 추천 공고]\n" + "\n".join(job_lines))

    return "\n\n".join(section for section in sections if section).strip() or "맞춤형 채용 공고 정보 없음"

def _build_job_posting_analysis(request: StartInterviewRequest) -> Dict[str, Any]:
    if request.job_description and request.job_description.strip():
        return {
            "status": "text_provided",
            "summary": request.job_description.strip(),
            "source": "text",
        }
    if request.job_image:
        analysis = _analyze_job_image_for_context(request.job_image)
        analysis["source"] = "image"
        return analysis
    return {
        "status": "not_provided",
        "summary": "맞춤형 채용 공고 정보 없음",
        "source": "none",
    }

def prepare_interview_context(request: StartInterviewRequest) -> Dict[str, Any]:
    job_title = _prompt_value(request.job_title)
    education = _prompt_value(request.education)
    experience = _prompt_value(request.experience)
    resume = _prompt_value(request.resume)
    interview_mode = normalize_interview_mode(request.interview_mode)
    mode_settings = _interview_mode_settings(interview_mode)

    job_posting_analysis = _build_job_posting_analysis(request)
    job_desc = str(job_posting_analysis.get("summary") or "").strip() or "맞춤형 채용 공고 정보 없음"

    context_jobs, recommended_jobs = _prepare_job_materials(
        job_title=job_title,
        experience=experience,
        education=education,
    )
    interview_job_context = _format_prepared_job_context(job_desc, context_jobs)

    try:
        guideline_selection = ReflectionService().select_prompt_guidelines(
            job_title=job_title,
            experience=experience,
            education=education,
            resume=resume,
            job_context=interview_job_context,
            interview_mode=interview_mode,
            limit=5,
        )
        reflection_guidelines = guideline_selection.text
    except Exception as e:
        logger.warning("Reflection guideline lookup failed: %s", e)
        reflection_guidelines = ""
        guideline_selection = None

    selected_voice = random.choice(list(VOICE_INTERVIEWER_NAMES.keys()))
    interviewer_name = VOICE_INTERVIEWER_NAMES[selected_voice]

    instructions = build_realtime_interviewer_prompt(
        interview_mode=interview_mode,
        interviewer_name=interviewer_name,
        job_title=job_title,
        education=education,
        experience=experience,
        resume=resume,
        job_description=interview_job_context,
        reflection_guidelines=reflection_guidelines
    )

    return {
        "interview_mode": interview_mode,
        "prompt_variant": f"realtime_interviewer_{interview_mode}",
        "job_title": job_title,
        "education": education,
        "experience": experience,
        "resume": resume,
        "mode_settings": mode_settings,
        "job_posting_analysis": job_posting_analysis,
        "job_posting_analysis_status": job_posting_analysis.get("status", ""),
        "context_jobs": context_jobs,
        "recommended_jobs": recommended_jobs,
        "interview_job_context": interview_job_context,
        "reflection_guidelines": reflection_guidelines,
        "guideline_selection": (
            guideline_selection.model_dump()
            if guideline_selection
            else {"text": "", "reflection_ids": [], "policy_ids": []}
        ),
        "selected_voice": selected_voice,
        "interviewer_name": interviewer_name,
        "instructions": instructions,
    }

@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(request: StartInterviewRequest):
    """
    지원자의 프로필을 받아 새로운 면접 세션을 생성하고, 
    OpenAI Realtime API 연동 토큰 발급 및 LangGraph 상태를 초기화합니다.
    """
    session_id = str(uuid.uuid4())
    context = prepare_interview_context(request)

    # 2. OpenAI Realtime 세션 생성
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-realtime-mini-2025-12-15",
        "modalities": ["audio", "text"],
        "instructions": context["instructions"],
        "voice": context["selected_voice"],
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
        "job_title": context["job_title"],
        "field": "",  # request에 없음
        "experience": context["experience"],
        "education": context["education"],
        "resume": context["resume"],
        "job_description": context["interview_job_context"],
        "job_posting_analysis": context["job_posting_analysis"],
        "job_posting_analysis_status": context["job_posting_analysis_status"],
        "reflection_guidelines": context["reflection_guidelines"],
        "guideline_selection": context["guideline_selection"],
        "reflection_source_ids": context["guideline_selection"].get("reflection_ids", []),
        "policy_source_ids": context["guideline_selection"].get("policy_ids", []),
        "interviewer_name": context["interviewer_name"],
        "interview_mode": context["interview_mode"],
        "interview_mode_label": context["mode_settings"]["label"],
        "interview_mode_guidance": context["mode_settings"]["guidance"],
        "prompt_variant": context["prompt_variant"],
        "major": "",  # request에 없음
        "messages": [],
        "saved_jobs": context["recommended_jobs"],
        "tool_traces": [],
        "status": "IN_PROGRESS"
    }
    interview_workflow.update_state({"configurable": {"thread_id": session_id}}, initial_state)
    
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
        "job_description": context["interview_job_context"],
        "job_posting_analysis": context["job_posting_analysis"],
        "job_posting_analysis_status": context["job_posting_analysis_status"],
        "interview_mode": context["interview_mode"],
        "prompt_variant": context["prompt_variant"],
        "guideline_selection": context["guideline_selection"],
        "reflection_source_ids": context["guideline_selection"].get("reflection_ids", []),
        "policy_source_ids": context["guideline_selection"].get("policy_ids", []),
        "prepared_jobs": context["recommended_jobs"],
        "context_jobs": context["context_jobs"],
        "tool_traces": [],
    }
    
    return StartInterviewResponse(
        session_id=session_id,
        ephemeral_token=ephemeral_token,
        message="면접 세션이 준비되었습니다.",
        prepared_jobs=context["recommended_jobs"],
        job_posting_analysis=context["job_posting_analysis"],
        interview_mode=context["interview_mode"],
        prompt_variant=context["prompt_variant"],
        guideline_selection=context["guideline_selection"],
    )

class ToolSearchRequest(BaseModel):
    query: str
    experience: str = ""
    education: str = ""

def _execute_search_job_with_context(
    *,
    query: str,
    experience: str,
    education: str,
    session_id: str | None = None,
) -> Dict[str, Any]:
    from app.engine.tools.job_search import search_korean_job_postings_with_trace

    result = search_korean_job_postings_with_trace(
        query=query,
        experience=experience,
        education=education,
    )
    jobs = _normalize_job_list(result.get("jobs", []), require_active=True)
    trace = dict(result.get("trace", {}))
    trace["filtered_count"] = len(jobs)

    if session_id:
        session = temp_sessions.setdefault(session_id, {})
        session["tool_traces"] = _dedupe_tool_traces(_normalize_tool_traces(session.get("tool_traces", [])) + [trace])
        session["prepared_jobs"] = _normalize_job_list(session.get("prepared_jobs", [])) + jobs
        session["prepared_jobs"] = _normalize_job_list(session["prepared_jobs"])[:6]
        try:
            interview_workflow.update_state(
                {"configurable": {"thread_id": session_id}},
                {
                    "saved_jobs": session["prepared_jobs"],
                    "tool_traces": session["tool_traces"],
                },
            )
        except Exception as exc:
            logger.warning("Failed to update tool trace state for session %s: %s", session_id, exc)

    return {"result": jobs, "trace": trace}

@router.post("/tools/search_job")
async def execute_search_job(request: ToolSearchRequest):
    """
    프론트엔드 WebRTC에서 OpenAI Realtime API가 툴 호출을 요청했을 때,
    실제 검색 툴을 실행하고 결과를 반환하는 엔드포인트입니다.
    """
    return _execute_search_job_with_context(
        query=request.query,
        experience=request.experience,
        education=request.education,
    )

@router.post("/{session_id}/tools/search_job")
async def execute_session_search_job(
    request: ToolSearchRequest,
    session_id: str = Path(..., description="면접 세션 ID"),
):
    session = temp_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="면접 세션을 찾을 수 없습니다.")

    return _execute_search_job_with_context(
        query=request.query,
        experience=str(session.get("experience") or ""),
        education=str(session.get("education") or ""),
        session_id=session_id,
    )

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

    prepared_jobs = temp_sessions.get(session_id, {}).get("prepared_jobs")
    source_jobs = prepared_jobs if isinstance(prepared_jobs, list) and prepared_jobs else request.saved_jobs
    report_jobs = _normalize_job_list(source_jobs)
    session_tool_traces = _normalize_tool_traces(temp_sessions.get(session_id, {}).get("tool_traces", []))
    request_tool_traces = _normalize_tool_traces(request.tool_traces)
    tool_traces = _dedupe_tool_traces(session_tool_traces + request_tool_traces)

    temp_sessions.setdefault(session_id, {})["status"] = "REPORT_QUEUED"
    background_tasks.add_task(
        generate_report_and_send_email,
        session_id=session_id,
        lc_messages=lc_messages,
        report_jobs=report_jobs,
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
    report_jobs: List[Dict[str, Any]],
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
            "saved_jobs": report_jobs,
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
            job_recommendations=evaluation.get("job_recommendations", []),
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
            saved_jobs=report_jobs,
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
        sections.append(f"""
                    <div class="section">
                        <h3 class="section-title">📌 이력서-직무 적합도</h3>
                        <div class="fit-score">{_html(role_fit.get('score', 0))} / 100 점</div>
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
