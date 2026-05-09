from typing import Dict, List
from urllib.parse import urlparse

import requests
from langchain_core.tools import tool
from app.core.config import settings

def _company_from_result(title: str, url: str) -> str:
    host = urlparse(url).netloc.replace("www.", "")
    domain_company = host.split(".")[0] if host else ""

    if " - " in title:
        return title.split(" - ", 1)[0].strip() or domain_company or "회사명 미상"
    if " | " in title:
        return title.split(" | ", 1)[0].strip() or domain_company or "회사명 미상"

    return domain_company or "회사명 미상"

def _format_job(title: str, content: str, url: str) -> Dict[str, str]:
    return {
        "company": _company_from_result(title, url),
        "title": title or "공고명 미상",
        "url": url or "",
        "content": content or "",
    }

@tool
def search_korean_job_postings(query: str) -> List[Dict[str, str]]:
    """
    한국의 주요 채용 사이트(원티드, 사람인 등)에서 특정 직무(query)에 대한
    최신 채용 공고 및 우대 조건(요구 기술 스택)을 검색합니다.
    면접관이 실무 중심의 꼬리 질문을 던지기 위해 실시간 트렌드를 파악할 때 사용합니다.
    실제 채용 공고 목록을 company, title, url, content 필드로 반환합니다.
    """
    print(f"[Tool: search_korean_job_postings] '{query}' 채용 정보 검색 중...")
    
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
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.TAVILY_API_KEY,
                "query": query,  # AI가 구체적인 조건(직무, 학력, 경력 등)을 포함해 생성하므로 그대로 사용
                "search_depth": "basic",
                "include_domains": [
                    "wanted.co.kr",
                    "saramin.co.kr",
                    "jobkorea.co.kr",
                    "jumpit.co.kr", 
                    "incruit.com"
                ],
                "max_results": 3
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        results: List[Dict[str, str]] = []
        for res in data.get("results", []):
            results.append(_format_job(
                title=res.get("title", ""),
                content=res.get("content", ""),
                url=res.get("url", ""),
            ))
            
        return results
        
    except Exception as e:
        print(f"❌ 검색 도구 실패: {e}")
        return []
