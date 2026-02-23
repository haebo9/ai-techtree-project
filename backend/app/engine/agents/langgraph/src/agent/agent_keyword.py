# 외부 모듈 import
import asyncio
from langchain_core.messages import AIMessage
from datetime import datetime

# 내부 모듈 import
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
        similar_items = await embedding_service.search_by_text(kw, k=1)
        if similar_items:
            # 가장 유사한 키워드 발견 -> 해당 키워드로 정보 대체
            best_match = similar_items[0]
            kw_data = best_match["data"]
            kw = kw_data["keyword_key"] # 상태 업데이트 (사용자가 입력한 오타 등을 보정)
            # TODO: 사용자에게 "혹시 {kw}를 찾으시나요?" 라고 물어보는 UX도 고려 가능

    # 3. 그래도 없으면 새로 생성 후 저장
    if not kw_data:
        # A. 키워드 생성 (Only Definition & Summary)
        # 퀴즈 생성 로직과 분리하여 설명만 생성
        generated_data = await agent_quiz.generate_explanation_only(kw)
        
        # LLM이 정제해준 키워드명(대소문자 등 보정됨)으로 DB에 한 번 더 조회를 시도
        generated_kw_key = generated_data.get("keyword")
        existing_kw = await keyword_service.get_keyword(generated_kw_key)
        
        if existing_kw:
            # 방금 새로 검색/생성하려 했으나, 정제된 이름과 완전히 동일한 키워드가 이미 DB에 있다면 그것을 재사용
            kw_data = existing_kw
            kw = generated_kw_key  # 상태 업데이트
        else:
            # DB 저장용 데이터
            db_data = {
                "keyword_key": generated_kw_key,
                "definition": generated_data.get("definition"),
                "summary": generated_data.get("summary"),
                "updated_at": datetime.now(),
            }
            
            # DB 저장
            created_kw = await keyword_service.create_keyword(db_data)
            kw_data = created_kw 
            kw = generated_kw_key # 상태 업데이트 (매우 중요: db 저장 키워드와 사용자 입력 대소문자 매칭을 위함)
            
            # 추천 엔진이 즉시 사용할 수 있도록 순차적으로 임베딩 인덱싱 대기
            await embedding_service.index_keyword(created_kw["keyword_key"])
        
    else:
        # 기존 데이터가 있는 경우 그대로 사용
        pass
    
    # 4. 퀴즈 정보 설정 (Initialize as None to trigger on-the-fly generation)
    # search_keyword 시점에는 퀴즈를 생성하지 않음. 
    # generate_quiz_node로 넘어갈 때 생성됨.
    quiz_info = None

    # 학습 시도 기록 (Star=0) 및 추천 키워드 계산 (순차적으로 실행하여 즉시 DB에 반영)
    user_id = state.get("user_id", "test_user@ai-techtree.com") # Default fallback test user email
    if user_id:
        # 1. 사용자 DB에 현재 키워드 기록을 저장합니다.
        await keyword_service.mark_learning_started(user_id, kw)
        
        # 2. 방금 저장된 학습 기록을 바탕으로 즉시 다음 추천 키워드를 계산하고 DB에 저장합니다.
        await embedding_service.calculate_recommendation(user_id)
                  
    return {
        "keyword": kw, # 업데이트된 키워드 (유사도 검색 시 변경 가능성)
        "keyword_data": kw_data,
        "current_question": None # Reset to trigger new quiz generation in next node
    }

async def recommend_keyword_node(state: KeywordState):
    """
    [Assessment Phase] Recommends a new keyword to the user.
    """
    import random
    from app.services.crud_user import user as user_crud
    
    user_id = state.get("user_id", "test_user@ai-techtree.com") # Default fallback test user email
    
    # 이메일 형식인지 체크하여 조회
    if "@" in user_id:
        user = await user_crud.get_by_email(user_id)
    else:
        user = await user_crud.get(user_id)
        
    recommendations = []
    
    # 1. 즉석 계산 시도 (사용자 학습 이력 기반)
    sim_items = await embedding_service.search_similar(user_id, k=10)
    if sim_items:
        recommendations = [item["keyword"] for item in sim_items]
    else:
        # Fallback: 임베딩 기반 검색 결과가 없거나 학습 이력이 없을 경우
        from app.services.crud_keyword import keyword as keyword_crud
        default_kws = await keyword_crud.get_multi(limit=20)
        # 사용자가 학습하지 않은(또는 별 3개가 아닌) 기본 키워드 추천
        available_kws = [k.keyword_key for k in default_kws]
        random.shuffle(available_kws)
        if user and user.keyword_progress:
            completed_kws = {k for k, v in user.keyword_progress.items() if v.star == 3}
            available_kws = [k for k in available_kws if k not in completed_kws]
        
        if available_kws:
            recommendations = available_kws[:10]
        else: 
            recommendations = ["Python", "Data Structure"]

    # 추가 필터링: 현재(방금) 학습한 키워드는 제외
    current_kw = state.get("keyword")
    if current_kw and current_kw in recommendations:
        recommendations.remove(current_kw)
        
    if not recommendations:
        # 최후의 수단 방어 (무한루프 방지)
        recommendations = ["Python", "Data Structure"] 

    # 2. 다음 키워드 제안 (Random Selection to vary response)
    # 목록 중 1~2개 정도를 무작위로 뽑아 매번 조금씩 다르게 제안합니다.
    num_to_select = min(len(recommendations), 2)
    selected_kws = random.sample(recommendations, num_to_select)
    
    # 별점(Star) 표시 추가
    formatted_kws = []
    for kw_name in selected_kws:
        star_count = 0
        if user and user.keyword_progress and kw_name in user.keyword_progress:
            star_count = user.keyword_progress[kw_name].star
        
        # 최대 3개의 별 (예: ⭐☆☆)
        star_count = min(star_count, 3)
        stars = "⭐" * star_count + "☆" * (3 - star_count)
        formatted_kws.append(f"{kw_name}({stars})")
    
    next_kw = ', '.join(formatted_kws)
    msg = f"다음으로는 **<{next_kw}>** 개념을 학습해보는 건 어떨까요?"
    
    return {
        # "keyword": next_kw, 
        "messages": [AIMessage(content=msg)]
    }

async def info_keyword_node(state: KeywordState):
    """
    [info Phase] Provides information or Trend about the keyword.
    """
    # TODO: Implement info logic
    return {"messages": [AIMessage(content="Keyword Info: (To be implemented)")]}
