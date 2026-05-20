import random
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.logger import get_logger
from app.engine.prompts.api_interview import build_realtime_interviewer_prompt, normalize_interview_mode
from app.services.reflection_service import ReflectionService

logger = get_logger(__name__)

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
            "목표 시간은 약 7분입니다. "
            "아이스브레이킹 후 자기소개와 지원동기를 각각 별도 질문으로 확인한 다음, "
            "대표 경험과 핵심 직무 질문을 짧고 밀도 있게 점검하세요. "
            "꼬리 질문은 답변 근거가 부족할 때만 적게 사용하고, 같은 경험에 오래 머무르지 마세요. "
            "평가 근거가 어느 정도 확보되면 추가 탐색보다 마지막 발언 기회를 주고 명확한 종료 멘트로 마무리하세요."
        ),
    },
    "long": {
        "label": "긴 면접",
        "guidance": (
            "목표 시간은 약 20분입니다. 아이스브레이킹 이후 자기소개와 지원동기를 각각 별도 질문으로 확인하고, "
            "이력서 기반 프로젝트/경험은 가능하면 서로 다른 경험 앵커를 2개 이상 활용하고, "
            "채용 공고 요건 기반 직무 질문, 협업/문제 해결, 기술 선택 이유, 지원 직무 관련 기술 질문까지 균형 있게 진행하세요. "
            "핵심 주제가 덜 다뤄졌다면 15분 안팎에서 조기 마무리하지 마세요. "
            "충분한 평가 근거가 확보되면 명확한 종료 멘트로 마무리하세요."
        ),
    },
}


def prompt_value(value: str | None, default: str = "정보 없음") -> str:
    cleaned = (value or "").strip()
    return cleaned if cleaned else default


def interview_mode_settings(mode: str | None) -> Dict[str, str]:
    normalized = normalize_interview_mode(mode)
    return INTERVIEW_MODE_GUIDANCE.get(normalized, INTERVIEW_MODE_GUIDANCE["long"])


def normalize_job_list(raw_jobs: Any, *, require_active: bool = False) -> List[Dict[str, str]]:
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


def normalize_tool_traces(raw_traces: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_traces, list):
        return []
    return [trace for trace in raw_traces if isinstance(trace, dict)]


def dedupe_tool_traces(raw_traces: Any) -> List[Dict[str, Any]]:
    deduped = []
    seen = set()
    for trace in normalize_tool_traces(raw_traces):
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


def analyze_job_image_for_context(image: str | None) -> Dict[str, Any]:
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


def prepare_job_materials(job_title: str, experience: str, education: str) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
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

    context_jobs = normalize_job_list(result)
    recommended_jobs = normalize_job_list(result, require_active=True)
    return context_jobs, recommended_jobs


def format_prepared_job_context(job_desc: str, prepared_jobs: List[Dict[str, str]]) -> str:
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


def build_job_posting_analysis(job_description: str | None, job_image: str | None) -> Dict[str, Any]:
    if job_description and job_description.strip():
        return {
            "status": "text_provided",
            "summary": job_description.strip(),
            "source": "text",
        }
    if job_image:
        analysis = analyze_job_image_for_context(job_image)
        analysis["source"] = "image"
        return analysis
    return {
        "status": "not_provided",
        "summary": "맞춤형 채용 공고 정보 없음",
        "source": "none",
    }


def build_manager_context(state: Dict[str, Any]) -> Dict[str, Any]:
    job_title = prompt_value(state.get("job_title"))
    education = prompt_value(state.get("education"))
    experience = prompt_value(state.get("experience"))
    resume = prompt_value(state.get("resume"))
    interview_mode = normalize_interview_mode(str(state.get("interview_mode") or "long"))
    mode_settings = interview_mode_settings(interview_mode)

    job_posting_analysis = build_job_posting_analysis(
        str(state.get("raw_job_description") or state.get("job_description") or ""),
        state.get("job_image"),
    )
    job_desc = str(job_posting_analysis.get("summary") or "").strip() or "맞춤형 채용 공고 정보 없음"

    context_jobs = state.get("context_jobs") or []
    recommended_jobs = state.get("prepared_jobs") or []
    interview_job_context = format_prepared_job_context(job_desc, context_jobs)

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
    except Exception as exc:
        logger.warning("Reflection guideline lookup failed: %s", exc)
        reflection_guidelines = ""
        guideline_selection = None
    guideline_selection_data = (
        guideline_selection.model_dump()
        if guideline_selection
        else {"text": "", "reflection_ids": [], "policy_ids": []}
    )

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
        reflection_guidelines=reflection_guidelines,
    )

    return {
        "interview_mode": interview_mode,
        "prompt_variant": f"realtime_interviewer_{interview_mode}",
        "job_title": job_title,
        "education": education,
        "experience": experience,
        "resume": resume,
        "interview_mode_label": mode_settings["label"],
        "interview_mode_guidance": mode_settings["guidance"],
        "job_description": interview_job_context,
        "job_posting_analysis": job_posting_analysis,
        "job_posting_analysis_status": job_posting_analysis.get("status", ""),
        "context_jobs": context_jobs,
        "saved_jobs": recommended_jobs,
        "prepared_jobs": recommended_jobs,
        "reflection_guidelines": reflection_guidelines,
        "guideline_selection": guideline_selection_data,
        "reflection_source_ids": guideline_selection_data.get("reflection_ids", []),
        "policy_source_ids": guideline_selection_data.get("policy_ids", []),
        "selected_voice": selected_voice,
        "voice": selected_voice,
        "interviewer_name": interviewer_name,
        "realtime_instructions": instructions,
        "instructions": instructions,
        "candidate_summary": str(state.get("candidate_summary") or ""),
        "interview_brief": str(state.get("interview_brief") or ""),
        "status": "IN_PROGRESS",
    }
