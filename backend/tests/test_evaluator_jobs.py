from langchain_core.messages import HumanMessage

from app.engine.nodes import evaluator as evaluator_module
from app.engine.nodes.evaluator import EvaluationSchema, evaluator_node


class FakeStructuredLlm:
    last_messages = None

    def invoke(self, messages):
        FakeStructuredLlm.last_messages = messages
        return EvaluationSchema(
            score=72,
            strengths=["직무 이해도가 있습니다."],
            weaknesses=["답변 구체성이 더 필요합니다."],
            qa_review=[],
            job_recommendations=[],
            communication_feedback={
                "summary": "답변이 간결합니다.",
                "strengths": ["핵심을 먼저 말합니다."],
                "habits_to_improve": ["근거를 더 붙이면 좋습니다."],
                "action_items": ["답변마다 사례를 연결하세요."],
            },
            self_intro_feedback={
                "original_summary": "자기소개성 답변을 짧게 했습니다.",
                "issues": ["이력서 경험 연결이 약합니다."],
                "improvement_direction": "이력서 경험과 직무를 연결합니다.",
                "improved_script": "안녕하세요. 저는 테스트 자동화 경험을 바탕으로 품질 문제를 개선해 온 지원자입니다.",
                "evidence_note": "실제 자기소개 답변을 참고했습니다.",
            },
            role_fit={
                "score": 74,
                "rationale": "테스트 자동화 경험이 목표 직무와 연결됩니다.",
                "matched_keywords": ["테스트 자동화"],
                "gaps": ["정량 성과 보완"],
            },
        )


class FakeLlm:
    def with_structured_output(self, schema):
        return FakeStructuredLlm()


def test_evaluator_uses_prepared_jobs_without_fallback_search(monkeypatch):
    monkeypatch.setattr(evaluator_module, "get_llm", lambda temperature=0.2: FakeLlm())
    prepared_jobs = [
        {
            "company": "테스트컴퍼니",
            "title": "AI QA 엔지니어",
            "url": "https://www.jobkorea.co.kr/Recruit/GI_Read/123",
            "content": "신입 가능. 테스트 자동화 경험 우대.",
        }
    ]

    result = evaluator_node({
        "user_id": "test@example.com",
        "job_title": "AI QA 엔지니어",
        "job_description": "맞춤형 공고",
        "resume": "테스트 자동화 프로젝트를 수행한 이력서 요약",
        "interview_mode_label": "짧은 면접",
        "messages": [HumanMessage(content="테스트 자동화 경험이 있습니다.")],
        "saved_jobs": prepared_jobs,
    })

    assert result["status"] == "COMPLETED"
    assert result["evaluation_result"]["job_recommendations"] == prepared_jobs
    assert "communication_feedback" in result["evaluation_result"]
    assert "self_intro_feedback" in result["evaluation_result"]
    assert "role_fit" in result["evaluation_result"]
    assert "테스트 자동화 프로젝트를 수행한 이력서 요약" in FakeStructuredLlm.last_messages[0].content


def test_evaluator_leaves_recommendations_empty_when_no_prepared_jobs(monkeypatch):
    monkeypatch.setattr(evaluator_module, "get_llm", lambda temperature=0.2: FakeLlm())

    result = evaluator_node({
        "user_id": "test@example.com",
        "job_title": "AI QA 엔지니어",
        "job_description": "맞춤형 공고",
        "messages": [HumanMessage(content="짧은 답변입니다.")],
        "saved_jobs": [],
    })

    assert result["status"] == "COMPLETED"
    assert result["evaluation_result"]["job_recommendations"] == []
