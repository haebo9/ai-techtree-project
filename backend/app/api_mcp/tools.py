from typing import List, Annotated
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from app.engine.tools.function_tool import (
    f_get_techtree_track,
    f_get_techtree_path,
    f_get_techtree_trend,
    f_get_techtree_subject,
    f_get_techtree_survey
)
from app.engine.tools.schema_tool import (
    TrackOutput, 
    PathOutput, 
    TrendOutput, 
    SubjectOutput,
    SurveyOutput
)

# Initialize FastMCP Server
# Set host to 0.0.0.0 to allow external access (Docker) and port 8200
# Enable stateless_http=True to allow clients (like Kakao MCP Player) to send POST requests
# without establishing an SSE session first. This fixes "Received request without session_id".
mcp = FastMCP("AI TechTree", host="0.0.0.0", port=8200, stateless_http=True)

# ---------------------------------------------------------
# Tool Definitions
# ---------------------------------------------------------
@mcp.tool()
def get_techtree_survey() -> SurveyOutput:
    """
    Returns a simple survey to understand the user's development experience and AI interests.

    [사용자 성향 진단] 
    - 목적: 사용자의 개발 연차와 관심 분야를 파악하기 위한 설문 질문을 생성합니다.
    - 사용 시점: 대화 초반, 사용자가 막연하게 학습 방법을 물어볼 때 사용합니다.
    - 입력 인자: 없음

    IMPORTANT FOR LLM: 
    - **Trigger Condition**: Use this tool ONLY when you lack sufficient information about the user's **'experience_level'** OR **'interests'**.
    - **Do NOT use**: If the user has already explicitly stated their development experience (e.g., "I'm a senior dev") AND their specific area of interest (e.g., "I want to build chatbots"). In that case, proceed directly to `get_techtree_track`.
    - **Goal**: Collect missing metadata to provide accurate recommendations.
    """
    data = f_get_techtree_survey()
    return SurveyOutput(**data)

@mcp.tool()
def get_techtree_track(
    interests: Annotated[List[str], Field(description="List of keywords. Pass ['ALL'] to see all available tracks.")],
    experience_level: Annotated[str, Field(description="User's experience level ('beginner', 'intermediate', 'expert').")]
) -> TrackOutput:
    """
    Analyzes user interests to recommend a track, OR lists all available tracks.

    [AI 직무 트랙 추천] 
    - 목적: 사용자 정보를 분석하여 적합한 커리어 트랙을 추천하거나 전체 목록을 보여줍니다.
    - 사용 시점: 설문 후 트랙을 정하거나, 트랙 종류를 물어볼 때 사용합니다.
    - 입력 인자:
        * interests: 관심 키워드 리스트 (예: ['LLM', 'backend'] 또는 ['ALL'])
        * experience_level: 개발 경력 수준 ('beginner', 'intermediate', 'expert')

    IMPORTANT FOR LLM: 
    - **Trigger Condition**: Use this tool IMMEDIATELY when the user asks "What should I study?" or "What tracks are available?".
    - **From Survey**: If you have the result from `get_techtree_survey`, use the EXACT list of keywords from the user's selected interest option as the `interests` argument. (e.g. `interests=['llm', 'langchain', ...]`)
    - **Show All Tracks**: If the user asks for a list of tracks or is unsure, Call this tool with `interests=["ALL"]`.
    """
    data = f_get_techtree_track(interests, experience_level)
    return TrackOutput(**data)

@mcp.tool()
def get_techtree_path(
    track_name: Annotated[str, Field(description="Exact name of the track (e.g., 'Track 1: AI Engineer').")]
) -> PathOutput:
    """
    Retrieves the full hierarchical curriculum roadmap for a specific track.

    [트랙별 학습 로드맵 조회] 
    - 목적: 선택한 트랙의 단계별 커리큘럼(Step-by-Step) 전체를 조회합니다.
    - 사용 시점: 특정 트랙의 구체적인 학습 순서나 과목 구성을 확인할 때 사용합니다.
    - 입력 인자:
        * track_name: 트랙의 정확한 명칭 (예: 'Track 1: AI Engineer')

    IMPORTANT FOR LLM: 
    - Use this structured data to create a "Step-by-Step Learning Plan" for the user.
    - **Focus on Sequence**: Emphasize the logical order of study (Step 1 -> Step 2 -> Step 3).
    - Step 3 (Application) focuses on projects and specialized domains.
    - Do NOT suggest specific time durations (e.g., "2 weeks") unless explicitly asked. Focus on **what to learn first** and **why**.
    """
    data = f_get_techtree_path(track_name)
    return PathOutput(**data)


@mcp.tool()
def get_techtree_subject(
    subject_name: Annotated[str, Field(description="The exact name of the subject (e.g., 'Vector DB', 'Python Syntax').")]
) -> SubjectOutput:
    """
    Retrieves detailed learning concepts (Lv1, Lv2, Lv3) for a specific subject.

    [과목별 상세 개념 학습] 
    - 목적: 특정 과목에서 학습해야 할 상세 개념(Lv1~Lv3)을 제공합니다.
    - 사용 시점: 로드맵의 특정 주제(예: Vector DB)에 대해 깊이 알고 싶을 때 사용합니다.
    - 입력 인자:
        * subject_name: 과목의 정확한 명칭 (예: 'Vector DB')

    IMPORTANT FOR LLM: 
    - **Trigger Condition**: Use this when the user asks for "What is X?", "What should I study in X?", or details about a specific roadmap item.
    - **Goal**: Explain the specific concepts (Lv1, Lv2, Lv3) required to master the subject.
    """
    data = f_get_techtree_subject(subject_name)
    return SubjectOutput(**data)

@mcp.tool()
def get_techtree_trend(
    keywords: Annotated[List[str], Field(description="List of technical keywords (e.g., ['LLM', 'Agent', 'RAG']). Include 3-5 related keywords for better tagging.")],
    category: Annotated[str, Field(description="Target content category ('tech_news', 'engineering', 'research', 'k_blog').")] = "k_blog"
) -> TrendOutput:
    """
    Performs a web search to provide the latest AI trend, news, and GitHub repositories based on keywords. Uses Tavily Search API with category-based domain filtering.

    [실시간 기술 트렌드 검색] 
    - 목적: 최신 뉴스, 기술 블로그(한국), 논문 등을 검색하여 제공합니다.
    - 사용 시점: 최신 기술 동향이나 실제 기업 적용 사례가 궁금할 때 사용합니다.
    - 입력 인자:
        * keywords: 검색 키워드 리스트 (예: ['RAG', '실무'])
        * category: 검색 카테고리
            - 'k_blog': 한국 기술 블로그 (추천)
            - 'tech_news': 글로벌 뉴스
            - 'engineering': 구현/코드 중심
            - 'research': 연구 논문

    IMPORTANT FOR LLM: 
    - "tech_news": Global Tech News & Trend (English sources like GeekNews, HackerNews).
    - "k_blog": **ALL Korean Content** (Korean Tech Blogs, News, Industry Cases). Select this for ANY Korean query.
    - "engineering": Implementation details (GitHub, WandB, LangChain).
    - "research": Academic papers (Arxiv).
    """
    data = f_get_techtree_trend(keywords, category)
    return TrendOutput(**data)

# No need to explicitly manually list MCP_TOOLS list if using @mcp.tool decorator with FastMCP's internal registry,
# but keeping it for reference if needed elsewhere. 
MCP_TOOLS = [
    get_techtree_survey,
    get_techtree_track,
    get_techtree_path,
    get_techtree_subject,
    get_techtree_trend,
]
