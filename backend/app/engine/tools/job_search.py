import requests
from langchain_core.tools import tool
from app.core.config import settings

@tool
def search_korean_job_postings(query: str) -> str:
    """
    한국의 주요 채용 사이트(원티드, 사람인 등)에서 특정 직무(query)에 대한
    최신 채용 공고 및 우대 조건(요구 기술 스택)을 검색합니다.
    면접관이 실무 중심의 꼬리 질문을 던지기 위해 실시간 트렌드를 파악할 때 사용합니다.
    """
    print(f"[Tool: search_korean_job_postings] '{query}' 채용 정보 검색 중...")
    
    if not settings.TAVILY_API_KEY:
        print("⚠️ TAVILY_API_KEY가 없어 Mock 데이터를 반환합니다.")
        return (
            f"[{query}] 최신 채용 트렌드 요약:\n"
            "- 필수 조건: python 언어, 4년제 학위\n"
            "- 우대 조건: 팀 프로젝트 경험, 성능 최적화 경험\n"
            "- 면접 팁: 기술을 '왜' 선택했는지 아키텍처 관점에서 질문하세요."
        )

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
        
        results = []
        for res in data.get("results", []):
            results.append(f"- {res.get('title')}: {res.get('content')} (링크: {res.get('url')})")
            
        summary = f"[{query}] 최신 채용 검색 결과:\n" + "\n".join(results)
        return summary
        
    except Exception as e:
        print(f"❌ 검색 도구 실패: {e}")
        return "현재 실시간 채용 정보를 가져올 수 없습니다. 검색 없이 기존 지식을 바탕으로 면접 질문을 이어가세요."
