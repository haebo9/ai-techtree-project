from app.engine.tools.job_search import (
    _build_fallback_queries,
    _build_search_query,
    _clean_job_title,
    _company_from_result,
    _dedupe_jobs,
    _format_job,
    _looks_expired,
    _is_relevant_to_role_query,
    _is_detail_job_url,
)


def test_detail_job_urls_are_accepted():
    assert _is_detail_job_url("https://www.jobkorea.co.kr/Recruit/GI_Read/123456")
    assert _is_detail_job_url("https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=123456")
    assert _is_detail_job_url("https://www.wanted.co.kr/wd/123456")
    assert _is_detail_job_url("https://www.jumpit.co.kr/position/123456")
    assert _is_detail_job_url("https://job.incruit.com/jobdb_info/jobpost.asp?job=123456")


def test_listing_urls_are_rejected():
    assert not _is_detail_job_url("https://www.jobkorea.co.kr/Search/?stext=QA%20Engineer")
    assert not _is_detail_job_url("https://www.saramin.co.kr/zf_user/search?searchword=QA%20Engineer")
    assert not _is_detail_job_url("https://www.jumpit.co.kr/positions?keyword=QA%20Engineer")
    assert not _is_detail_job_url("https://www.wanted.co.kr/search?query=QA%20Engineer")


def test_listing_titles_are_rejected_even_on_supported_domains():
    assert _format_job(
        title="'QA engineer' 관련 채용공고 | 총 339건의 검색결과",
        content="잡코리아 검색결과입니다.",
        url="https://www.jobkorea.co.kr/Recruit/GI_Read/123456",
    ) is None


def test_valid_job_result_is_formatted():
    job = _format_job(
        title="QA 엔지니어 (QA Engineer) - 마인드에이아이 채용",
        content="주요업무: 서비스 품질 관리 및 자동화 테스트",
        url="https://www.jobkorea.co.kr/Recruit/GI_Read/123456",
    )

    assert job == {
        "company": "마인드에이아이",
        "title": "QA 엔지니어 (QA Engineer)",
        "url": "https://www.jobkorea.co.kr/Recruit/GI_Read/123456",
        "content": "주요업무: 서비스 품질 관리 및 자동화 테스트",
    }


def test_dedupe_jobs_by_url():
    jobs = [
        {"company": "A", "title": "공고 A", "url": "https://www.wanted.co.kr/wd/1"},
        {"company": "A", "title": "공고 A", "url": "https://www.wanted.co.kr/wd/1"},
        {"company": "B", "title": "공고 B", "url": "https://www.wanted.co.kr/wd/2"},
    ]

    assert _dedupe_jobs(jobs) == [jobs[0], jobs[2]]


def test_search_query_biases_toward_detail_pages():
    query = _build_search_query("QA Engineer")

    assert "QA Engineer" in query
    assert "상세" in query
    assert "자격요건" in query
    assert "-검색결과" in query


def test_fallback_queries_target_detail_url_patterns():
    queries = _build_fallback_queries("QA Engineer")

    assert any("site:wanted.co.kr/wd" in query for query in queries)
    assert any("site:jobkorea.co.kr/Recruit/GI_Read" in query for query in queries)
    assert any("site:saramin.co.kr/zf_user/jobs/relay/view" in query for query in queries)


def test_jobkorea_company_first_title_is_split_cleanly():
    title = "신한투자증권 채용 - AI솔루션부 QA Manager 경력직 채용 | 잡코리아"
    url = "https://www.jobkorea.co.kr/Recruit/GI_Read/49050287"

    assert _company_from_result(title, url) == "신한투자증권"
    assert _clean_job_title(title) == "AI솔루션부 QA Manager 경력직 채용"


def test_expired_job_result_is_rejected():
    assert _format_job(
        title="QA 엔지니어 - 마인드에이아이 채용",
        content="접수마감된 공고입니다. 지난 채용정보입니다.",
        url="https://www.jobkorea.co.kr/Recruit/GI_Read/123456",
    ) is None


def test_active_deadline_hint_is_not_treated_as_expired():
    text = "접수기간/방법. 남은시간 D-11. 채용시 마감될 수 있습니다."

    assert not _looks_expired("QA 엔지니어 채용", text)
    assert _format_job(
        title="QA 엔지니어 - 마인드에이아이 채용",
        content=text,
        url="https://www.jobkorea.co.kr/Recruit/GI_Read/123456",
    ) is not None


def test_search_query_excludes_expired_jobs():
    query = _build_search_query("QA Engineer")

    assert "-접수마감" in query
    assert "-모집마감" in query
    assert "-마감된공고" in query


def test_raw_content_is_used_to_reject_expired_jobs():
    assert _format_job(
        title="QA 엔지니어 - 마인드에이아이 채용",
        content="주요업무: 테스트 자동화",
        raw_content="이 공고는 접수마감되었습니다.",
        url="https://www.jobkorea.co.kr/Recruit/GI_Read/123456",
    ) is None


def test_wanted_bracket_company_is_used():
    assert _company_from_result(
        "[카카오엔터테인먼트] QA/테스트 엔지니어(신입/인턴) 채용 공고",
        "https://www.wanted.co.kr/wd/2083",
    ) == "카카오엔터테인먼트"


def test_qa_query_requires_qa_related_title():
    assert _is_relevant_to_role_query("QA Engineer", "독일 차량 Infotainment Software 검증 엔지니어 채용")
    assert not _is_relevant_to_role_query("QA Engineer", "Senior/Lead software engineer")
