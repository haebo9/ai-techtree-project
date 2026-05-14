import asyncio

from app.api import interview as interview_api
from app.api.interview import _normalize_job_list, prepare_interview_context
from app.schemas_api.interview import StartInterviewRequest


def test_normalize_job_list_keeps_context_jobs_without_active_hint():
    jobs = [
        {
            "company": "A",
            "title": "AI 엔지니어",
            "url": "https://www.wanted.co.kr/wd/1",
            "content": "주요업무: AI 서비스 개발. 자격요건: Python.",
        }
    ]

    assert _normalize_job_list(jobs) == jobs


def test_normalize_job_list_filters_only_expired_report_recommendations():
    active = {
        "company": "A",
        "title": "AI 엔지니어",
        "url": "https://www.wanted.co.kr/wd/1",
        "content": "상시채용. 주요업무: AI 서비스 개발.",
    }
    unclear = {
        "company": "B",
        "title": "AI 엔지니어",
        "url": "https://www.wanted.co.kr/wd/2",
        "content": "주요업무: AI 서비스 개발.",
    }

    expired = {
        "company": "C",
        "title": "AI 엔지니어",
        "url": "https://www.wanted.co.kr/wd/3",
        "content": "접수마감된 공고입니다.",
    }

    assert _normalize_job_list([active, unclear, expired], require_active=True) == [
        {**active, "deadline_status": "active"},
        {**unclear, "deadline_status": "unknown"},
    ]


def test_prepare_interview_context_uses_image_analysis_for_job_description(monkeypatch):
    monkeypatch.setattr(
        interview_api,
        "_analyze_job_image_for_context",
        lambda image: {
            "status": "image_analyzed",
            "summary": "회사명: 테스트\n직무명: 언어공학자\n주요업무: 데이터 평가",
        },
    )
    monkeypatch.setattr(interview_api, "_prepare_job_materials", lambda **kwargs: ([], []))

    class FakeReflectionService:
        def get_prompt_guidelines(self, **kwargs):
            return ""

    monkeypatch.setattr(interview_api, "ReflectionService", lambda: FakeReflectionService())

    context = prepare_interview_context(
        StartInterviewRequest(
            user_id="test@example.com",
            report_email="report@example.com",
            job_title="언어공학자",
            experience="신입",
            education="학사",
            resume="LLM 프로젝트",
            job_image="data:image/png;base64,abc",
            interview_mode="short",
        )
    )

    assert context["job_posting_analysis_status"] == "image_analyzed"
    assert "직무명: 언어공학자" in context["interview_job_context"]
    assert "직무명: 언어공학자" in context["instructions"]
    assert context["interview_mode"] == "short"
    assert context["prompt_variant"] == "realtime_interviewer_short"


def test_prepare_interview_context_falls_back_to_long_for_unknown_mode(monkeypatch):
    monkeypatch.setattr(interview_api, "_prepare_job_materials", lambda **kwargs: ([], []))

    class FakeReflectionService:
        def get_prompt_guidelines(self, **kwargs):
            return ""

    monkeypatch.setattr(interview_api, "ReflectionService", lambda: FakeReflectionService())

    context = prepare_interview_context(
        StartInterviewRequest(
            user_id="test@example.com",
            report_email="report@example.com",
            job_title="AI Engineer",
            experience="신입",
            education="학사",
            resume="LLM 프로젝트",
            interview_mode="unexpected",
        )
    )

    assert context["interview_mode"] == "long"
    assert context["prompt_variant"] == "realtime_interviewer_long"
    assert "면접 시간 운영: 실전 면접" in context["instructions"]
    assert "짧은 면접" not in context["instructions"]


def test_start_interview_does_not_register_realtime_search_tools(monkeypatch):
    captured_payload = {}

    class FakeRealtimeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"client_secret": {"value": "ephemeral-test-token"}}

    def fake_post(url, *, headers, json, timeout):
        captured_payload.update(json)
        return FakeRealtimeResponse()

    monkeypatch.setattr(interview_api.requests, "post", fake_post)
    monkeypatch.setattr(
        interview_api.interview_workflow,
        "update_state",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        interview_api,
        "prepare_interview_context",
        lambda request: {
            "interview_mode": "long",
            "prompt_variant": "realtime_interviewer_long",
            "job_title": "AI Engineer",
            "education": "학사",
            "experience": "신입",
            "resume": "LLM 프로젝트",
            "mode_settings": {"label": "긴 면접", "guidance": "약 20분"},
            "job_posting_analysis": {"status": "not_provided"},
            "job_posting_analysis_status": "not_provided",
            "context_jobs": [],
            "recommended_jobs": [],
            "interview_job_context": "맞춤형 채용 공고 정보 없음",
            "reflection_guidelines": "",
            "guideline_selection": {"text": "", "reflection_ids": [], "policy_ids": []},
            "selected_voice": "sage",
            "interviewer_name": "Mina",
            "instructions": "면접관 프롬프트",
        },
    )

    response = asyncio.run(
        interview_api.start_interview(
            StartInterviewRequest(
                user_id="test@example.com",
                report_email="report@example.com",
                job_title="AI Engineer",
                experience="신입",
                education="학사",
                resume="LLM 프로젝트",
                interview_mode="long",
            )
        )
    )

    assert response.ephemeral_token == "ephemeral-test-token"
    assert "tools" not in captured_payload
    assert "tool_choice" not in captured_payload
