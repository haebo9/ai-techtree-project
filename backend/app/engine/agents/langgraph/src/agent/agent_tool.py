from typing import List, Annotated
from langchain_core.tools import tool
from app.engine.tools.v1.function_tool import (
    f_get_techtree_trend,
    f_get_techtree_track,
    f_get_techtree_path,
    f_get_techtree_subject
)

# ==========================================
# Tool Wrappers (LangChain Compatible)
# ==========================================

@tool
def search_trend(keywords: List[str], category: str = "k_blog") -> dict:
    """
    [검색/트렌드] 최신 기술 뉴스, 블로그, Github 트렌드 등을 검색합니다.
    '찾아줘', '검색해줘', '요즘 뜨는거', '정보 알려줘' 등의 요청 시 사용하세요. 
    Category: 
        - 'k_blog': (기본값) 한국어 기술 블로그/뉴스. 대부분의 한국어 질문에 적합.
        - 'tech_news': 해외 뉴스 (영어).
        - 'research': 학술 논문 (Arxiv 등).
        - 'engineering': 구현/코드 (Github, HuggingFace).
    """
    return f_get_techtree_trend(keywords, category)

@tool
def recommend_track(interests: List[str], experience_level: str = "intermediate") -> dict:
    """
    [커리큘럼 추천] 사용자의 관심사나 경력에 맞춰 AI 트랙(커리큘럼)을 추천합니다.
    '뭐 공부할까?', '추천해줘', '어떤 트랙이 있어?' 등의 요청 시 사용하세요. 
    전체 목록을 보려면 interests=['ALL']을 사용하세요.
    """
    return f_get_techtree_track(interests, experience_level)

@tool
def get_roadmap(track_name: str) -> dict:
    """
    [로드맵 조회] 특정 트랙의 전체 커리큘럼(단계별 학습 내용)을 조회합니다.
    '로드맵 보여줘', '학습 경로 알려줘', '무수 순서로 배워야 해?' 등의 요청 시 사용하세요.
    track_name은 정확한 트랙 명칭이어야 합니다 (예: 'Track 1: AI Engineer').
    """
    return f_get_techtree_path(track_name)

@tool
def explain_concept(subject_name: str) -> dict:
    """
    [개념 설명/상세 조회] 특정 기술 용어나 주제에 대한 상세 내용(Lv1, Lv2, Lv3 개념)을 조회합니다.
    'Vector DB가 뭐야?', 'Transformer 설명해줘', '상세 내용 알려줘' 등의 요청 시 사용하세요.
    """
    return f_get_techtree_subject(subject_name)

# Tool List Export
techtree_tools = [search_trend, recommend_track, get_roadmap, explain_concept]