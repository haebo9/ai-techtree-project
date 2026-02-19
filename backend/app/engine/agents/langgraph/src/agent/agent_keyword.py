import asyncio
from langchain_core.messages import AIMessage
from app.engine.agents.langgraph.src.agent.state import KeywordState
from app.services.keyword_service import keyword_service
from app.services.embedding_service import embedding_service
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
    
    # 1. DB 조회 시도 (Exact Match)
    kw_data = await keyword_service.get_keyword(kw)
    
    # 2. 없다면 벡터 유사도 검색 시도 (Semantic Match)
    if not kw_data:
        similar_items = await embedding_service.search_similar(kw, k=1)
        if similar_items:
            # 가장 유사한 키워드 발견 -> 해당 키워드로 정보 대체
            best_match = similar_items[0]
            kw_data = best_match["data"]
            kw = kw_data["keyword_key"] # 상태 업데이트 (사용자가 입력한 오타 등을 보정)
            # TODO: 사용자에게 "혹시 {kw}를 찾으시나요?" 라고 물어보는 UX도 고려 가능

    # 3. 그래도 없으면 새로 생성 후 저장
    if not kw_data:
        # 통합 생성 (설명 + 퀴즈)
        kw_data = await agent_quiz.generate_quiz_and_explanation(kw)
        created_kw = await keyword_service.create_keyword(kw_data)
        
        # [Async] 백그라운드 임베딩 인덱싱 (사용자 응답 지연 방지)
        # 키워드가 생성되자마자 벡터화 작업을 큐에 던짐
        asyncio.create_task(embedding_service.index_keyword(created_kw["keyword_key"]))
        
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
        "keyword": kw, # 업데이트된 키워드 (유사도 검색 시 변경 가능성)
        "keyword_data": kw_data,
        "current_question": quiz_info, # 다음 단계를 위해 저장
        "messages": [AIMessage(content=msg_content)]
    }

async def recommend_keyword_node(state: KeywordState):
    """
    [Assessment Phase] Recommends a new keyword to the user.
    """
    kw = state.get("keyword")
    
    # 1. 현재 학습한 키워드와 연관된 키워드 추천
    recommendations = []
    if kw:
        # 현재 키워드와 유사한 상위 3개 검색
        sim_items = await embedding_service.search_similar(kw, k=3)
        # 자기 자신 제외하고 추천 목록 구성
        recommendations = [item["keyword"] for item in sim_items if item["keyword"] != kw]
    
    # 2. 추천 결과가 없거나 부족하면 랜덤 추천 (혹은 기본 커리큘럼)
    if not recommendations:
        # TODO: 추후 커리큘럼 기반 추천 로직으로 고도화 필요
        recommendations = ["Java", "Python", "Spring Boot"] # Fallback

    # 3. 다음 키워드 제안 메시지 작성
    next_kw = recommendations[0]
    msg = f"Good job! Next, how about learning **{next_kw}**? It's related to what you just learned."
    
    return {
        # "keyword": next_kw, # (선택) 다음 키워드로 바로 상태 전이할지, 유저 선택 기다릴지 결정 필요. 현재는 제안만.
        "messages": [AIMessage(content=msg)]
    }

async def info_keyword_node(state: KeywordState):
    """
    [info Phase] Provides information or Trend about the keyword.
    """
    # TODO: Implement info logic
    return {"messages": [AIMessage(content="Keyword Info: (To be implemented)")]}
