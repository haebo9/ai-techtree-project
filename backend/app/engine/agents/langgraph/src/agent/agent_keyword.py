from langchain_core.messages import AIMessage
from app.engine.agents.langgraph.src.agent.state import KeywordState
from app.services.keyword_service import keyword_service
from app.engine.agents.langgraph.src.agent import agent_quiz

# ==========================================
# Nodes
# ==========================================
# 사용자 요청과 관련된 키워드를 DB에서 찾고 없으면 새롭게 생성
async def search_keyword_node(state: KeywordState):
    """
    [Content Phase] 
    1. Searches (or generates) info for the keyword.
    2. Explains it to the user.
    """
    kw = state.get("keyword")
    if not kw:
        return {"messages": [AIMessage(content="Please specify a keyword to learn.")]}
    
    # DB 조회 시도
    kw_data = await keyword_service.get_keyword(kw)
    
    # 없으면 새로 생성 후 저장
    if not kw_data:
        # 통합 생성 (설명 + 퀴즈)
        kw_data = await agent_quiz.generate_quiz_and_explanation(kw)
        await keyword_service.create_keyword(kw_data)
    elif not kw_data.get("quiz_question"):
        # 퀴즈 정보가 없으면 보충 (기존 데이터 유지)
        new_data = await agent_quiz.generate_quiz_and_explanation(kw)
        kw_data.update({
            "quiz_question": new_data.get("quiz_question"),
            "quiz_options": new_data.get("quiz_options"),
            "quiz_answer": new_data.get("quiz_answer")
        })
        # (Optional) DB 업데이트가 필요하지만, 일단 메모리상에서만 사용
    
    # 퀴즈 정보 추출 및 설정
    quiz_info = {
        "question_text": kw_data.get("quiz_question"),
        "options": kw_data.get("quiz_options"),
        "answer": kw_data.get("quiz_answer")
    }

    msg_content = (
        f"## 📚 Concept: {kw}\n\n"
        f"**Definition**: {kw_data.get('definition')}\n\n"
        f"**Summary**: {kw_data.get('summary')}\n\n"
        f"*(Preparing a quiz for you...)*"
    )
                  
    return {
        "keyword_data": kw_data,
        "current_question": quiz_info, # 다음 단계를 위해 저장
        "messages": [AIMessage(content=msg_content)]
    }

async def recommend_keyword_node(state: KeywordState):
    """
    [Assessment Phase] Recommends a new keyword to the user.
    """
    # TODO: Implement recommendation logic
    return {"messages": [AIMessage(content="Recommended keyword: (To be implemented)")]}

async def info_keyword_node(state: KeywordState):
    """
    [info Phase] Provides information or Trend about the keyword.
    """
    # TODO: Implement info logic
    return {"messages": [AIMessage(content="Keyword Info: (To be implemented)")]}
