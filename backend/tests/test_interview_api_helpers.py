from app.api.interview import _normalize_job_list


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
