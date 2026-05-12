import asyncio

import pytest
from fastapi import BackgroundTasks
from pydantic import ValidationError

from app.api import interview as interview_api
from app.schemas_api.interview import EndInterviewRequest, StartInterviewRequest


def test_start_request_requires_report_email():
    with pytest.raises(ValidationError):
        StartInterviewRequest(
            user_id="test@example.com",
            job_title="AI Engineer",
            experience="신입",
            education="학사",
            resume="이력 요약",
        )


def test_end_interview_queues_report_generation_without_evaluation(monkeypatch):
    session_id = "async-session"
    interview_api.temp_sessions[session_id] = {
        "report_email": "report@example.com",
        "prepared_jobs": [],
    }
    background_tasks = BackgroundTasks()
    request = EndInterviewRequest(
        transcripts=[{"role": "user", "text": "답변입니다."}],
        saved_jobs=[],
        interview_date="2026년 5월 11일",
        interview_duration="7분 10초",
    )

    response = asyncio.run(interview_api.end_interview(background_tasks, request, session_id))

    assert response.status == "queued"
    assert interview_api.temp_sessions[session_id]["status"] == "REPORT_QUEUED"
    assert len(background_tasks.tasks) == 1


def test_background_report_sends_email_and_cleans_sensitive_session(monkeypatch):
    class FakeWorkflow:
        def update_state(self, config, state):
            self.updated_state = state

        def invoke(self, value, config):
            return {
                "job_title": "AI Engineer",
                "experience": "신입",
                "education": "학사",
                "messages": [],
                "evaluation_result": {
                    "score": 80,
                    "strengths": ["명확한 직무 관심"],
                    "weaknesses": ["정량 지표 보완"],
                    "qa_review": [],
                    "job_recommendations": [],
                },
            }

    sent = []
    reflected = []
    session_id = "background-session"
    interview_api.temp_sessions[session_id] = {
        "report_email": "report@example.com",
        "resume": "민감한 이력 요약",
        "job_description": "민감한 공고 원문",
        "interview_mode": "short",
        "prepared_jobs": [],
        "context_jobs": [],
    }
    monkeypatch.setattr(interview_api, "interview_workflow", FakeWorkflow())
    monkeypatch.setattr(interview_api, "_send_report_email", lambda request: sent.append(request))
    monkeypatch.setattr(interview_api, "safe_generate_and_store_reflections", lambda **kwargs: reflected.append(kwargs))

    interview_api.generate_report_and_send_email(
        session_id=session_id,
        lc_messages=[],
        report_jobs=[],
        transcripts=[{"role": "user", "text": "답변입니다."}],
        interview_date="2026년 5월 11일",
        interview_duration="7분 10초",
    )

    session = interview_api.temp_sessions[session_id]
    assert session["status"] == "REPORT_SENT"
    assert "report_email" not in session
    assert "resume" not in session
    assert "job_description" not in session
    assert sent[0].email == "report@example.com"
    assert sent[0].score == 80
    assert reflected
    assert reflected[0]["interview_mode"] == "short"
