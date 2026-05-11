from langchain_core.messages import HumanMessage

from app.engine.nodes import evaluator as evaluator_module
from app.engine.nodes.evaluator import EvaluationSchema, evaluator_node


class FakeStructuredLlm:
    def invoke(self, messages):
        return EvaluationSchema(
            score=72,
            strengths=["직무 이해도가 있습니다."],
            weaknesses=["답변 구체성이 더 필요합니다."],
            qa_review=[],
            job_recommendations=[],
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
        "messages": [HumanMessage(content="테스트 자동화 경험이 있습니다.")],
        "saved_jobs": prepared_jobs,
    })

    assert result["status"] == "COMPLETED"
    assert result["evaluation_result"]["job_recommendations"] == prepared_jobs


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
