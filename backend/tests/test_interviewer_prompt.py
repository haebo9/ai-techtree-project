from app.engine.prompts.api_interview import INTERVIEWER_SYSTEM_PROMPT
from app.api.interview import VOICE_INTERVIEWER_NAMES


def test_prompt_treats_entered_job_title_as_authoritative():
    prompt = INTERVIEWER_SYSTEM_PROMPT.format(
        interviewer_name="Mina",
        job_title="QA Engineer",
        education="학사",
        experience="신입",
        resume="테스트 자동화 프로젝트 경험",
        job_description="맞춤형 채용 공고 정보 없음",
        reflection_guidelines="",
    )

    assert "시니어 면접관 Mina" in prompt
    assert "지원 직무가 '정보 없음'이 아니라면 이미 확정된 정보입니다." in prompt
    assert '"어떤 직무에 지원하셨나요?"라고 다시 묻지 말고' in prompt
    assert "QA Engineer 직무를 선택한 이유" in prompt
    assert "간단한 자기소개와 함께 QA Engineer 직무에 관심을 갖게 된 계기" in prompt


def test_prompt_sets_ten_minute_interview_target():
    prompt = INTERVIEWER_SYSTEM_PROMPT.format(
        interviewer_name="Mina",
        job_title="QA Engineer",
        education="학사",
        experience="신입",
        resume="테스트 자동화 프로젝트 경험",
        job_description="맞춤형 채용 공고 정보 없음",
        reflection_guidelines="",
    )

    assert "10분은 강제 종료 조건이 아니라 운영 목표입니다." in prompt
    assert "6-8개의 핵심 질문" in prompt
    assert "오늘 면접은 여기까지 진행하겠습니다" in prompt
    assert "명확한 종료 멘트 전에는 면접이 자동 종료되지 않습니다." in prompt


def test_prompt_starts_with_icebreaking_before_interview_questions():
    prompt = INTERVIEWER_SYSTEM_PROMPT.format(
        interviewer_name="Mina",
        job_title="QA Engineer",
        education="학사",
        experience="신입",
        resume="테스트 자동화 프로젝트 경험",
        job_description="맞춤형 채용 공고 정보 없음",
        reflection_guidelines="",
    )

    assert "바로 기술 질문으로 들어가지 말고" in prompt
    assert "가벼운 아이스브레이킹" in prompt
    assert "오늘 컨디션은 어떠세요?" in prompt
    assert "실제 날씨를 모르면 날씨를 단정하지 말고" in prompt


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
