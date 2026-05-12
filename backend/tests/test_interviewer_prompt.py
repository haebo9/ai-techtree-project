from app.engine.prompts.api_interview import build_realtime_interviewer_prompt
from app.api.interview import VOICE_INTERVIEWER_NAMES


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
    assert "목표 시간은 약 20분입니다." in prompt
    assert "오늘 면접은 여기까지 진행하겠습니다" in prompt
    assert "명확한 종료 멘트 전에는 면접이 자동 종료되지 않습니다." in prompt


def test_prompt_starts_with_icebreaking_before_interview_questions():
    prompt = _prompt()

    assert "바로 기술 질문으로 들어가지 말고" in prompt
    assert "가벼운 아이스브레이킹" in prompt
    assert "오늘 컨디션은 어떠세요?" in prompt
    assert "준비는 괜찮으셨나요?" in prompt
    assert "지금 바로 시작해도 괜찮으실까요?" in prompt
    assert "표현 중 하나를 자연스럽게 바꿔 사용하세요" in prompt
    assert "실제 날씨를 모르면 날씨를 단정하지 말고" in prompt
    assert "첫 발화에서는 자기소개, 지원 동기, 프로젝트 질문을 함께 묻지 마세요." in prompt
    assert "지원자가 아이스브레이킹 질문에 답한 다음 턴에서만" in prompt


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
        interview_mode="short",
    )
    long_prompt = _prompt()

    assert "면접 시간 운영: 짧은 면접" in short_prompt
    assert "목표 시간은 약 7분입니다." in short_prompt
    assert "핵심 직무 질문은 최대 3개" in short_prompt
    assert "꼬리 질문은 전체 면접에서 최대 1회" in short_prompt
    assert "성과, 사용 도구, 팀 피드백 중 하나를 확인했다면" in short_prompt
    assert "\"마지막으로\", \"마무리로\", \"끝으로\"라는 표현을 사용했다면 그 질문이 최종 질문입니다." in short_prompt
    assert "지원자가 답변한 뒤에는 추가 확인 질문을 하지 말고 종료 멘트로 마무리하세요." in short_prompt
    assert "면접 시간 운영: 실전 면접" in long_prompt
    assert "목표 시간은 약 20분입니다." in long_prompt
    assert "이력서 기반 대표 프로젝트 1-2개" in long_prompt
    assert "실패·개선 경험" in long_prompt
    assert "최소 6개 안팎의 핵심 질문" in long_prompt


def test_long_prompt_does_not_include_short_mode_pressure():
    long_prompt = _prompt()

    assert "짧은 면접" not in long_prompt
    assert "목표 시간은 약 7분" not in long_prompt
    assert "대표 경험 1개만" not in long_prompt
    assert "꼬리 질문은 전체 면접에서 최대 1회" not in long_prompt
