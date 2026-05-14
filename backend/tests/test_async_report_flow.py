import asyncio

import pytest
from fastapi import BackgroundTasks
from pydantic import ValidationError

from app.api import interview as interview_api
from app.schemas_api.email import SendEmailRequest
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
                    "communication_feedback": {
                        "summary": "답변이 간결합니다.",
                        "strengths": ["핵심을 먼저 말합니다."],
                        "habits_to_improve": ["근거를 한 문장 더 붙이면 좋습니다."],
                        "action_items": ["답변마다 사례를 하나씩 연결하세요."],
                    },
                    "self_intro_feedback": {
                        "original_summary": "AI 엔지니어 관심을 짧게 설명했습니다.",
                        "issues": ["이력서 경험과 연결이 약합니다."],
                        "improvement_direction": "프로젝트 경험과 직무 관심을 먼저 연결합니다.",
                        "improved_script": "안녕하세요. 저는 AI 품질 개선 경험을 바탕으로 제품 문제를 구조적으로 해결해 온 지원자입니다.",
                        "evidence_note": "실제 자기소개 답변을 참고했습니다.",
                    },
                    "role_fit": {
                        "score": 76,
                        "rationale": "이력서의 AI 경험이 목표 직무와 연결됩니다.",
                        "matched_keywords": ["AI", "품질 개선"],
                        "gaps": ["정량 성과 보완"],
                    },
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
        tool_traces=[{"status": "no_results", "reason": "No Tavily results were returned."}],
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
    assert sent[0].communication_feedback["summary"] == "답변이 간결합니다."
    assert sent[0].self_intro_feedback["improved_script"].startswith("안녕하세요")
    assert sent[0].role_fit["score"] == 76
    assert reflected
    assert reflected[0]["interview_mode"] == "short"


def test_report_email_html_renders_extended_feedback_sections():
    html = interview_api._build_report_email_html(
        SendEmailRequest(
            email="report@example.com",
            score=80,
            strengths=["강점"],
            weaknesses=["개선점"],
            communication_feedback={
                "summary": "말이 빠르지만 핵심은 분명합니다.",
                "strengths": ["핵심을 먼저 말합니다."],
                "habits_to_improve": ["답변 끝맺음을 명확히 하세요."],
                "action_items": ["30초 단위로 답변을 끊어 연습하세요."],
            },
            self_intro_feedback={
                "original_summary": "프로젝트 경험을 짧게 소개했습니다.",
                "issues": ["직무 연결이 약합니다."],
                "improvement_direction": "이력서 경험을 직무 문제 해결 역량과 연결합니다.",
                "improved_script": "안녕하세요. 저는 사용자 문제를 데이터로 정의하고 해결해 온 지원자입니다.",
                "evidence_note": "실제 자기소개 답변을 참고했습니다.",
            },
            role_fit={
                "score": 82,
                "rationale": "서비스 기획 경험과 직무 요구가 잘 맞습니다.",
                "matched_keywords": ["서비스 기획", "데이터 분석"],
                "gaps": ["정량 성과 보완"],
            },
            transcripts=[
                {"role": "ai", "text": "자기소개 부탁드립니다."},
                {"role": "user", "text": "안녕하세요. 저는 서비스 기획 경험이 있습니다."},
            ],
        )
    )

    assert "말투/답변 습관 피드백" in html
    assert "추천 자기소개 멘트" in html
    assert "이력서-직무 적합도" in html
    assert "82%" in html
    assert "transcript-ai" in html
    assert "transcript-user" in html
    assert "안녕하세요. 저는 사용자 문제를 데이터로 정의하고 해결해 온 지원자입니다." in html
