from langgraph.prebuilt import ToolNode

# ==========================================
# 1. Tool Definitions (실제 동작 로직) - TEST
# backend/app/engine/tools 에 정의해두고 사용
# ==========================================
from langchain_core.tools import tool
@tool
def search_keyword_tool(keyword: str) -> str:
    """주어진 키워드에 대한 기술 면접 질문과 답변 데이터를 검색합니다."""
    # TODO: 실제 DB 조회 로직 구현 필요
    return f"'{keyword}'에 대한 면접 질문 데이터입니다. (DB 연동 필요)"

@tool
def recommend_keyword_tool(current_keyword: str) -> str:
    """현재 학습 중인 키워드와 연관된 다음 학습 키워드를 추천합니다."""
    # TODO: 연관도 로직 구현 필요
    return f"'{current_keyword}'와 관련된 다음 키워드는 'Spring Boot'입니다. (연관도 로직 필요)"

@tool
def get_user_level_tool(user_id: str) -> str:
    """사용자의 현재 기술 레벨을 조회합니다."""
    # TODO: 사용자 정보 조회 로직 구현 필요
    return "초급"

# ==========================================
# 2. ToolNode 생성 (LangGraph용 래퍼)
# ==========================================

# Supervisor에서 사용할 도구들
supervisor_tools = [search_keyword_tool, recommend_keyword_tool, get_user_level_tool]
supervisor_tools_node = ToolNode(tools=supervisor_tools)

# Quiz에서 사용할 도구들 (필요시 추가)
quiz_tools = [search_keyword_tool, recommend_keyword_tool]
quiz_tools_node = ToolNode(tools=quiz_tools)