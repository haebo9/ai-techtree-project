from app.api.interview import VOICE_INTERVIEWER_NAMES
from app.engine.prompts.api_interview import build_realtime_interviewer_prompt


def _prompt(**overrides):
    data = {
        "interviewer_name": "Mina",
        "interview_mode": "long",
        "job_title": "QA Engineer",
        "education": "학사",
        "experience": "신입",
        "resume": "테스트 자동화 프로젝트 경험",
        "job_description": "맞춤형 채용 공고 정보 없음",
        "reflection_guidelines": "",
    }
    data.update(overrides)
    return build_realtime_interviewer_prompt(**data)


def test_common_prompt_keeps_required_realtime_guardrails():
    prompt = _prompt()

    assert "시니어 면접관 Mina" in prompt
    assert "파일을 읽었습니다" in prompt
    assert "시스템이 드러나는 표현은 쓰지 마세요" in prompt
    assert "짧은 인사와 가벼운 아이스브레이킹" in prompt
    assert '"어떤 직무에 지원하셨나요?"라고 다시 묻지 말고' in prompt
    assert "지원자가 면접 종료 의사를 명확히 밝히면" in prompt
    assert "평가는 최종 리포트에서만 제공됩니다" in prompt


def test_common_prompt_keeps_reflection_strong_but_scoped():
    prompt = _prompt()

    assert "운영 지침으로 적극 반영" in prompt
    assert "최근 보정 지침보다 먼저 적용" in prompt
    assert "현재 대화 맥락과 충돌하는 지침은" in prompt
    assert "우선적인 운영 보정값" not in prompt
    assert "모든 발화는 두 문장 이내" not in prompt


def test_interview_mode_prompts_have_distinct_operating_goals():
    short_prompt = _prompt(interview_mode="short")
    long_prompt = _prompt(interview_mode="long")

    assert "대표 경험과 핵심 직무 질문을 짧고 밀도 있게 점검" in short_prompt
    assert "목표 시간은 약 7분 내외입니다" in short_prompt
    assert "꼬리 질문은 적게 사용" in short_prompt
    assert "핵심 직무 질문은 최대 3개" not in short_prompt
    assert "꼬리 질문은 전체 면접에서 최대 1회" not in short_prompt

    assert "직무 역량, 프로젝트, 협업/문제 해결까지 깊이 있게 진행" in long_prompt
    assert "목표 시간은 약 20분 내외입니다" in long_prompt
    assert "큰 대화 흐름은 프로젝트 경험, 핵심 직무 역량, 기술 선택 이유, 협업/문제 해결" in long_prompt
    assert "시간 관리는 주제 자체를 생략하기보다 꼬리 질문의 깊이로 조절" in long_prompt
    assert "답변 맥락상 중요한 항목을 선택" in long_prompt
    assert "최소 6개" not in long_prompt


def test_every_realtime_voice_has_interviewer_name():
    assert VOICE_INTERVIEWER_NAMES == {
        "alloy": "Alex",
        "ash": "Noah",
        "ballad": "Ethan",
        "coral": "Sophia",
        "echo": "Daniel",
        "sage": "Mina",
        "shimmer": "Yuna",
        "verse": "Jin",
    }
