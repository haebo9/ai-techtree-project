from langchain_core.messages import HumanMessage

from app.engine.nodes import manager as manager_module
from app.engine.nodes import evaluator as evaluator_module
from app.engine.prompts.reflection_analyzer import REFLECTION_ANALYZER_SYSTEM_PROMPT


class _CaptureLlmResponse:
    tool_calls = []


class _CaptureManagerLlm:
    last_messages = None

    def bind_tools(self, _tools):
        return self

    def invoke(self, messages):
        _CaptureManagerLlm.last_messages = messages
        return _CaptureLlmResponse()


class _CaptureStructuredLlm:
    last_messages = None

    def invoke(self, messages):
        _CaptureStructuredLlm.last_messages = messages
        from app.engine.nodes.evaluator import EvaluationSchema

        return EvaluationSchema(
            score=0,
            strengths=["근거 부족"],
            weaknesses=["근거 부족"],
            qa_review=[],
            communication_feedback={
                "summary": "근거 부족",
                "strengths": ["근거 부족"],
                "habits_to_improve": ["근거 부족"],
                "action_items": ["근거 부족"],
            },
            self_intro_feedback={
                "original_summary": "근거 부족",
                "issues": ["근거 부족"],
                "improvement_direction": "근거 부족",
                "improved_script": "근거 부족",
                "evidence_note": "근거 부족",
            },
            role_fit={
                "score": 0,
                "rationale": "근거 부족",
                "matched_keywords": [],
                "gaps": ["근거 부족"],
            },
        )


class _CaptureEvalLlm:
    def with_structured_output(self, _schema):
        return _CaptureStructuredLlm()


def test_manager_prompt_includes_single_search_and_missing_job_fallback(monkeypatch):
    monkeypatch.setattr(manager_module, "get_llm", lambda temperature=0: _CaptureManagerLlm())

    manager_module.manager_agent_node({"job_title": "정보 없음", "job_description": "", "messages": []})
    prompt = _CaptureManagerLlm.last_messages[0].content

    assert "`search_korean_job_postings` 툴을 1회 호출" in prompt
    assert "직무명이 '정보 없음'이거나 공백이면 툴을 호출하지 말고" in prompt


def test_evaluator_prompt_includes_schema_and_anti_hallucination_rules(monkeypatch):
    monkeypatch.setattr(evaluator_module, "get_llm", lambda temperature=0.2: _CaptureEvalLlm())

    evaluator_module.evaluator_node(
        {
            "user_id": "user",
            "job_title": "백엔드 개발자",
            "job_description": "요건",
            "resume": "이력서",
            "messages": [HumanMessage(content="답변")],
        }
    )
    prompt = _CaptureStructuredLlm.last_messages[0].content

    assert "EvaluationSchema 구조에 정확히 맞춰" in prompt
    assert "스키마에 없는 필드를 생성하지 마세요" in prompt
    assert "대화/이력서/공고에 없는 사실을 새로 만들지 마세요" in prompt


def test_reflection_prompt_enforces_actionable_structured_rules():
    assert "스키마에 맞는 필드만" in REFLECTION_ANALYZER_SYSTEM_PROMPT
    assert "근거가 약하면 개수를 억지로 채우지 말고 빈 리스트" in REFLECTION_ANALYZER_SYSTEM_PROMPT
    assert "prompt_hint는 실행 가능한 동사로 시작" in REFLECTION_ANALYZER_SYSTEM_PROMPT
