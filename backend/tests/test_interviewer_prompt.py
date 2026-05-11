from app.engine.prompts.api_interview import INTERVIEWER_SYSTEM_PROMPT
from app.api.interview import INTERVIEW_MODE_GUIDANCE, VOICE_INTERVIEWER_NAMES


def _prompt(**overrides):
    data = {
        "interviewer_name": "Mina",
        "interview_mode_label": "긴 면접",
        "interview_mode_guidance": INTERVIEW_MODE_GUIDANCE["long"]["guidance"],
        "job_title": "QA Engineer",
        "education": "학사",
        "experience": "신입",
        "resume": "테스트 자동화 프로젝트 경험",
        "job_description": "맞춤형 채용 공고 정보 없음",
        "reflection_guidelines": "",
    }
    data.update(overrides)
    return INTERVIEWER_SYSTEM_PROMPT.format(**data)


def test_prompt_treats_entered_job_title_as_authoritative():
    prompt = _prompt()

    assert "시니어 면접관 Mina" in prompt
    assert "지원 직무가 '정보 없음'이 아니라면 이미 확정된 정보입니다." in prompt
    assert '"어떤 직무에 지원하셨나요?"라고 다시 묻지 말고' in prompt
    assert "QA Engineer 직무를 선택한 이유" in prompt
    assert "간단한 자기소개와 함께 QA Engineer 직무에 관심을 갖게 된 계기" in prompt


def test_prompt_sets_ten_minute_interview_target():
    prompt = _prompt()

    assert "선택된 목표 시간은 강제 종료 조건이 아니라" in prompt
    assert "목표 시간은 약 15분입니다." in prompt
    assert "오늘 면접은 여기까지 진행하겠습니다" in prompt
    assert "명확한 종료 멘트 전에는 면접이 자동 종료되지 않습니다." in prompt


def test_prompt_starts_with_icebreaking_before_interview_questions():
    prompt = _prompt()

    assert "바로 기술 질문으로 들어가지 말고" in prompt
    assert "가벼운 아이스브레이킹" in prompt
    assert "오늘 컨디션은 어떠세요?" in prompt
    assert "실제 날씨를 모르면 날씨를 단정하지 말고" in prompt
    assert "첫 발화에서는 자기소개, 지원 동기, 프로젝트 질문을 함께 묻지 마세요." in prompt
    assert "지원자가 컨디션 질문에 답한 다음 턴에서만" in prompt


def test_prompt_recovers_when_answer_misses_question_intent():
    prompt = _prompt()

    assert "답변이 방금 질문의 의도와 다르거나 일부 질문에만 답했다면" in prompt
    assert "누락된 질문을 부드럽게 다시 요청하세요" in prompt
    assert "자기소개와 지원 동기 답변이 확보되기 전에는" in prompt


def test_prompt_avoids_in_interview_evaluation_feedback():
    prompt = _prompt()

    assert '"부족합니다", "더 고민해 보세요", "개선이 필요합니다"' in prompt
    assert "평가는 최종 리포트에서만 제공됩니다." in prompt


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


def test_interview_mode_guidance_supports_short_and_long_modes():
    short_prompt = _prompt(
        interview_mode_label=INTERVIEW_MODE_GUIDANCE["short"]["label"],
        interview_mode_guidance=INTERVIEW_MODE_GUIDANCE["short"]["guidance"],
    )
    long_prompt = _prompt()

    assert "면접 모드: 짧은 면접" in short_prompt
    assert "목표 시간은 약 5분입니다." in short_prompt
    assert "핵심 직무 질문 2-3개" in short_prompt
    assert "면접 모드: 긴 면접" in long_prompt
    assert "목표 시간은 약 15분입니다." in long_prompt
    assert "직무 역량 질문 4-6개" in long_prompt
