import re
from typing import Dict, List
from urllib.parse import urlparse

import requests
from langchain_core.tools import tool
from app.core.config import settings

SUPPORTED_DOMAINS = (
    "wanted.co.kr",
    "saramin.co.kr",
    "jobkorea.co.kr",
    "jumpit.co.kr",
    "incruit.com",
)

DETAIL_URL_PATTERNS = {
    "wanted.co.kr": (r"/wd/\d+",),
    "saramin.co.kr": (r"/zf_user/jobs/relay/view", r"/zf_user/jobs/view"),
    "jobkorea.co.kr": (r"/Recruit/GI_Read", r"/recruit/gi_read"),
    "jumpit.co.kr": (r"/position/\d+",),
    "incruit.com": (r"/jobdb_info/jobpost\.asp", r"/jobdb_info/popupjobpost\.asp"),
}

LIST_URL_KEYWORDS = (
    "/search",
    "/recruit/joblist",
    "/recruit/joblist?",
    "/zf_user/search",
    "/zf_user/jobs/list",
    "/jobs/list",
    "/position?",
    "/positions?",
)

LIST_TITLE_PATTERNS = (
    r"검색결과",
    r"채용정보",
    r"채용공고\s*\|\s*총",
    r"관련\s+채용공고",
    r"전체\s+채용",
    r"채용\s*목록",
)

ACTIVE_DEADLINE_PATTERNS = (
    r"\bD-\d+\b",
    r"오늘\s*마감",
    r"내일\s*마감",
    r"상시\s*채용",
    r"상시\s*모집",
    r"채용\s*시\s*마감",
    r"수시\s*채용",
    r"남은\s*시간",
)

EXPIRED_POSTING_PATTERNS = (
    r"마감된\s*공고",
    r"마감된\s*채용",
    r"마감된\s*포지션",
    r"접수\s*마감",
    r"모집\s*마감",
    r"채용\s*마감",
    r"공고\s*마감",
    r"지원\s*마감",
    r"이미\s*마감",
    r"마감되었습니다",
    r"마감됐습니다",
    r"지난\s*채용",
    r"종료된\s*공고",
    r"closed",
    r"expired",
)

ROLE_KEYWORDS = (
    "QA",
    "Engineer",
    "엔지니어",
    "개발자",
    "매니저",
    "Manager",
    "테스트",
    "검증",
    "기획자",
    "디자이너",
    "마케터",
)

def _normalize_profile_condition(value: str | None) -> str:
    return " ".join((value or "").split()).strip()

def _build_profile_terms(experience: str | None = "", education: str | None = "") -> str:
    experience = _normalize_profile_condition(experience)
    education = _normalize_profile_condition(education)
    terms = []

    if experience:
        if "신입" in experience:
            terms.extend(["신입", "경력무관", "주니어", "인턴"])
        elif "1~3" in experience or "1-3" in experience:
            terms.extend(["1년", "2년", "3년", "주니어"])
        elif "3~5" in experience or "3-5" in experience:
            terms.extend(["3년", "4년", "5년"])
        elif "5" in experience:
            terms.extend(["5년 이상", "시니어"])
        else:
            terms.append(experience)

    if education:
        if "고졸" in education:
            terms.extend(["고졸", "학력무관"])
        elif "전문학사" in education:
            terms.extend(["전문학사", "초대졸", "학력무관"])
        elif "학사" in education:
            terms.extend(["대졸", "학사", "4년제", "학력무관"])
        elif "석사" in education or "박사" in education:
            terms.append(education)
        else:
            terms.append(education)

    return " ".join(terms)

def _build_search_query(query: str, experience: str | None = "", education: str | None = "") -> str:
    cleaned_query = " ".join(query.split()).strip()
    if not cleaned_query:
        cleaned_query = "개발자"
    profile_terms = _build_profile_terms(experience, education)

    return (
        f"{cleaned_query} {profile_terms} 채용공고 상세 모집공고 주요업무 자격요건 "
        "지원자격 회사명 D- 상시채용 채용시마감 "
        "-검색결과 -채용정보 -목록 -접수마감 -모집마감 -마감된공고"
    )

def _build_fallback_queries(query: str, experience: str | None = "", education: str | None = "") -> List[str]:
    cleaned_query = " ".join(query.split()).strip() or "개발자"
    profile_terms = _build_profile_terms(experience, education)
    query_with_profile = f"{cleaned_query} {profile_terms}".strip()
    return [
        f"site:wanted.co.kr/wd {query_with_profile} 채용공고",
        f"site:jobkorea.co.kr/Recruit/GI_Read {query_with_profile} 채용공고",
        f"site:saramin.co.kr/zf_user/jobs/relay/view {query_with_profile} 채용공고",
        f"site:jumpit.co.kr/position {query_with_profile} 채용공고",
        f"site:incruit.com/jobdb_info/jobpost.asp {query_with_profile} 채용공고",
    ]

def _domain_from_url(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")

def _is_supported_domain(url: str) -> bool:
    host = _domain_from_url(url)
    return any(host == domain or host.endswith(f".{domain}") for domain in SUPPORTED_DOMAINS)

def _is_detail_job_url(url: str) -> bool:
    if not url or not _is_supported_domain(url):
        return False

    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")
    path_with_query = f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path
    lowered = path_with_query.lower()

    if any(keyword in lowered for keyword in LIST_URL_KEYWORDS):
        return False

    for domain, patterns in DETAIL_URL_PATTERNS.items():
        if host == domain or host.endswith(f".{domain}"):
            return any(re.search(pattern, path_with_query, re.IGNORECASE) for pattern in patterns)

    return False

def _looks_like_listing_result(title: str, content: str) -> bool:
    return any(re.search(pattern, title, re.IGNORECASE) for pattern in LIST_TITLE_PATTERNS)

def _has_active_deadline_hint(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in ACTIVE_DEADLINE_PATTERNS)

def _looks_expired(title: str, content: str) -> bool:
    text = f"{title} {content}"
    if _has_active_deadline_hint(text):
        return False
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in EXPIRED_POSTING_PATTERNS)

def classify_job_deadline_status(job: Dict[str, str]) -> str:
    text = f"{job.get('title', '')} {job.get('content', '')}"
    if _looks_expired(job.get("title", ""), job.get("content", "")):
        return "expired"
    if _has_active_deadline_hint(text):
        return "active"
    return "unknown"

def is_recommendable_active_job(job: Dict[str, str]) -> bool:
    return classify_job_deadline_status(job) != "expired"

def _company_from_result(title: str, url: str) -> str:
    host = urlparse(url).netloc.lower().replace("www.", "")
    domain_company = next(
        (domain.split(".")[0] for domain in SUPPORTED_DOMAINS if host == domain or host.endswith(f".{domain}")),
        host.split(".")[0] if host else "",
    )
    bracket_match = re.match(r"^\[([^\]]+)\]", title)
    if bracket_match:
        bracket_text = bracket_match.group(1).strip()
        if bracket_text:
            return bracket_text

    if " - " in title:
        parts = [part.strip() for part in title.split(" - ") if part.strip()]
        first_company = re.sub(r"\s*채용.*$", "", parts[0]).strip()
        if first_company != parts[0] and first_company:
            return _strip_site_noise(first_company)
        for part in parts[1:]:
            company = re.sub(r"\s*(채용|공채|모집|잡코리아|사람인|원티드|점핏|인크루트).*$", "", part).strip()
            if company:
                return _strip_site_noise(company)
    if " | " in title:
        title = title.split(" | ", 1)[0].strip()

    bracketless_title = re.sub(r"^\[[^\]]+\]\s*", "", title).strip()
    for keyword in ROLE_KEYWORDS:
        index = bracketless_title.lower().find(keyword.lower())
        if index > 0:
            company = bracketless_title[:index].strip(" -_/·")
            if company:
                return _strip_site_noise(company)

    return domain_company or "회사명 미상"

def _strip_site_noise(text: str) -> str:
    return re.sub(r"\s*(잡코리아|사람인|원티드|점핏|인크루트).*$", "", text).strip(" -_|")

def _clean_job_title(title: str) -> str:
    title = _strip_site_noise(title)

    if " | " in title:
        title = title.split(" | ", 1)[0].strip()

    title = re.sub(r"^\[[^\]]+\]\s*", "", title).strip()

    if " - " not in title:
        return title

    parts = [part.strip() for part in title.split(" - ") if part.strip()]
    if len(parts) < 2:
        return title

    if re.search(r"\s*채용.*$", parts[0]):
        return " - ".join(parts[1:]).strip()

    if any(re.search(r"\s*(채용|공채|모집).*$", part) for part in parts[1:]):
        return parts[0]

    return title

def _is_relevant_to_role_query(query: str, title: str) -> bool:
    query_lower = query.lower()
    title_lower = title.lower()

    if re.search(r"\bqa\b|quality\s*assurance|테스트|검증|품질", query_lower):
        return any(
            keyword in title_lower
            for keyword in ("qa", "sqa", "test", "테스트", "검증", "품질")
        )

    return True

def _extract_required_years(text: str) -> int | None:
    years = []
    for pattern in (
        r"경력\s*(\d+)\s*년\s*이상",
        r"(\d+)\s*년\s*이상",
        r"경력\s*(\d+)\s*년",
        r"(\d+)\s*년차",
    ):
        years.extend(int(match) for match in re.findall(pattern, text))
    return max(years) if years else None

def _is_relevant_to_profile(experience: str | None, education: str | None, title: str, content: str) -> bool:
    del education

    experience = _normalize_profile_condition(experience)
    text = f"{title} {content}"
    required_years = _extract_required_years(text)

    if not experience:
        return True

    if "신입" in experience:
        if re.search(r"신입|경력\s*무관|경력무관|인턴|주니어|junior", text, re.IGNORECASE):
            return True
        return required_years is None

    if "1~3" in experience or "1-3" in experience:
        return required_years is None or required_years <= 3

    if "3~5" in experience or "3-5" in experience:
        return required_years is None or required_years <= 5

    return True

def _format_job(title: str, content: str, url: str, raw_content: str = "") -> Dict[str, str] | None:
    title = " ".join((title or "").split()).strip()
    content = " ".join((content or "").split()).strip()
    raw_content = " ".join((raw_content or "").split()).strip()
    url = (url or "").strip()
    filter_text = raw_content or content

    if not title or not _is_detail_job_url(url):
        return None
    if _looks_like_listing_result(title, content):
        return None
    if _looks_expired(title, filter_text):
        return None

    return {
        "company": _company_from_result(title, url),
        "title": _clean_job_title(title),
        "url": url,
        "content": content,
    }

def _dedupe_jobs(jobs: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen_urls = set()
    deduped = []

    for job in jobs:
        url = job.get("url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(job)

    return deduped

def _fetch_tavily_results(query: str, role_query: str, max_results: int) -> List[Dict[str, str]]:
    response = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": settings.TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "include_domains": list(SUPPORTED_DOMAINS),
            "include_raw_content": True,
            "max_results": max_results,
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    jobs: List[Dict[str, str]] = []
    for res in data.get("results", []):
        if not isinstance(res, dict):
            continue
        job = _format_job(
            title=str(res.get("title", "")),
            content=str(res.get("content", "")),
            url=str(res.get("url", "")),
            raw_content=str(res.get("raw_content", "")),
        )
        if job and _is_relevant_to_role_query(role_query, job["title"]):
            jobs.append(job)

    return jobs

@tool
def search_korean_job_postings(query: str, experience: str = "", education: str = "") -> List[Dict[str, str]]:
    """
    한국의 주요 채용 사이트(원티드, 사람인 등)에서 특정 직무(query)에 대한
    최신 채용 공고 및 우대 조건(요구 기술 스택)을 검색합니다.
    면접관이 실무 중심의 꼬리 질문을 던지기 위해 실시간 트렌드를 파악할 때 사용합니다.
    실제 채용 공고 목록을 company, title, url, content 필드로 반환합니다.
    """
    print(f"[Tool: search_korean_job_postings] '{query}' 채용 정보 검색 중...")
    search_query = _build_search_query(query, experience=experience, education=education)
    
    if not settings.TAVILY_API_KEY:
        print("⚠️ TAVILY_API_KEY가 없어 Mock 데이터를 반환합니다.")
        return [
            {
                "company": "Mock Company",
                "title": f"{query} 포지션",
                "url": "",
                "content": "필수 조건: python 언어, 4년제 학위 / 우대 조건: 팀 프로젝트 경험, 성능 최적화 경험",
            }
        ]

    try:
        results = _fetch_tavily_results(search_query, role_query=query, max_results=10)
        results = [
            job for job in results
            if _is_relevant_to_profile(experience, education, job.get("title", ""), job.get("content", ""))
        ]

        for fallback_query in _build_fallback_queries(query, experience=experience, education=education):
            if len(_dedupe_jobs(results)) >= 3:
                break
            try:
                fallback_results = _fetch_tavily_results(fallback_query, role_query=query, max_results=5)
                results.extend(
                    job for job in fallback_results
                    if _is_relevant_to_profile(experience, education, job.get("title", ""), job.get("content", ""))
                )
            except Exception as fallback_error:
                print(f"⚠️ 상세 공고 보강 검색 실패: {fallback_error}")

        if not _dedupe_jobs(results) and (experience or education):
            broad_results = _fetch_tavily_results(_build_search_query(query), role_query=query, max_results=10)
            results.extend(
                job for job in broad_results
                if _is_relevant_to_profile(experience, education, job.get("title", ""), job.get("content", ""))
            )

            for fallback_query in _build_fallback_queries(query):
                if len(_dedupe_jobs(results)) >= 3:
                    break
                try:
                    fallback_results = _fetch_tavily_results(fallback_query, role_query=query, max_results=5)
                    results.extend(
                        job for job in fallback_results
                        if _is_relevant_to_profile(experience, education, job.get("title", ""), job.get("content", ""))
                    )
                except Exception as fallback_error:
                    print(f"⚠️ 상세 공고 보강 검색 실패: {fallback_error}")
            
        return _dedupe_jobs(results)[:3]
        
    except Exception as e:
        print(f"❌ 검색 도구 실패: {e}")
        return []
