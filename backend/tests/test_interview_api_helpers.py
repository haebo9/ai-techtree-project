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


def test_session_search_uses_server_session_profile(monkeypatch):
    calls = []

    def fake_search(*, query, experience="", education=""):
        calls.append({"query": query, "experience": experience, "education": education})
        return {
            "jobs": [
                {
                    "company": "테스트",
                    "title": "언어공학자",
                    "url": "https://www.wanted.co.kr/wd/1",
                    "content": "상시채용",
                }
            ],
            "trace": {
                "tool_name": "search_job_postings",
                "query": query,
                "status": "success",
                "reason": "",
                "raw_count": 1,
                "filtered_count": 1,
            },
        }

    monkeypatch.setattr("app.engine.tools.job_search.search_korean_job_postings_with_trace", fake_search)
    monkeypatch.setattr(
        interview_api.interview_workflow,
        "update_state",
        lambda *args, **kwargs: None,
    )

    interview_api.temp_sessions["tool-session"] = {
        "experience": "신입",
        "education": "학사(4년제)",
        "prepared_jobs": [],
        "tool_traces": [],
    }

    session_result = asyncio.run(
        interview_api.execute_session_search_job(
            interview_api.ToolSearchRequest(
                query="언어공학자 채용",
                experience="프론트가 보낸 경력",
                education="프론트가 보낸 학력",
            ),
            "tool-session",
        )
    )

    assert calls[0]["experience"] == "신입"
    assert calls[0]["education"] == "학사(4년제)"
    assert session_result["result"][0]["company"] == "테스트"
    assert interview_api.temp_sessions["tool-session"]["tool_traces"]
