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
        # A. 키워드 생성 (Only Definition & Summary)
        # 퀴즈 생성 로직과 분리하여 DB에 저장될 데이터만 먼저 생성
        # TODO: generate_quiz_and_explanation 함수가 통합되어 있어 분리 필요.
        #       일단 전체 생성 후, DB 저장 시에만 필터링하도록 수정.
        generated_data = await agent_quiz.generate_quiz_and_explanation(kw)
        
        # DB 저장용 데이터 (퀴즈 정보 제외)
        db_data = {
            "keyword_key": generated_data.get("keyword"),
            "definition": generated_data.get("definition"),
            "summary": generated_data.get("summary"),
            # "quiz_question" 등은 제외
        }
        
        created_kw = await keyword_service.create_keyword(db_data)
        kw_data = created_kw # DB 모델 (퀴즈 없음)
        
        # 메모리용 퀴즈 데이터 (사용자 응답용)
        # kw_data(DB모델)에는 퀴즈가 없으므로 generated_data에서 가져옴
        quiz_from_gen = {
            "quiz_question": generated_data.get("quiz_question"),
            "quiz_options": generated_data.get("quiz_options"),
            "quiz_answer": generated_data.get("quiz_answer")
        }
        
        # [Async] 백그라운드 임베딩 인덱싱 (사용자 응답 지연 방지)
        asyncio.create_task(embedding_service.index_keyword(created_kw["keyword_key"]))
        
    else:
        # 기존 데이터가 있는 경우, 퀴즈만 새로 생성 (DB 저장 X, 메모리 사용 O)
        # 매번 새로운 퀴즈를 풀게 하기 위함 (선택 사항)
        generated_quiz = await agent_quiz.generate_quiz_and_explanation(kw)
        quiz_from_gen = {
            "quiz_question": generated_quiz.get("quiz_question"),
            "quiz_options": generated_quiz.get("quiz_options"),
            "quiz_answer": generated_quiz.get("quiz_answer")
        }
    
    # 퀴즈 정보 추출 및 설정
    quiz_info = {
        "question_text": quiz_from_gen.get("quiz_question"),
        "options": quiz_from_gen.get("quiz_options"),
        "answer": quiz_from_gen.get("quiz_answer")
    }

    # [Async] 학습 시도 기록 (Star=0)
    # 퀴즈를 풀지 않아도 "시도함"으로 표시
    user_id = state.get("user_id", "test_user") # Default fallback
    if user_id:
        asyncio.create_task(keyword_service.mark_learning_started(user_id, kw))

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
    import random
    from app.services.crud_user import user as user_crud
    
    user_id = "test_user" # TODO: state에서 user_id 가져오기
    user = await user_crud.get(user_id)
    
    recommendations = []
    
    # 1. Pre-calculated 추천 목록 확인
    if user and user.recommended_keywords:
        recommendations = user.recommended_keywords
    
    # 2. 추천 목록이 없으면 즉석 계산 시도 (Backup)
    if not recommendations:
        kw = state.get("keyword")
        if kw:
            # 현재 키워드와 유사한 상위 3개 검색
            sim_items = await embedding_service.search_similar(kw, k=3)
            # 자기 자신 제외하고 추천 목록 구성
            recommendations = [item["keyword"] for item in sim_items if item["keyword"] != kw]
            
            # [Async] 다음을 위해 백그라운드 추천 갱신 요청
            asyncio.create_task(embedding_service.calculate_recommendation(user_id))

    # 3. 그래도 없으면 Fallback
    if not recommendations:
        recommendations = ["Java", "Python", "Spring Boot"] 

    # 4. 다음 키워드 제안 (Random Selection to vary response)
    next_kw = random.choice(recommendations)
    msg = f"Good job! Next, how about learning **{next_kw}**? It's related to what you just learned."
    
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
