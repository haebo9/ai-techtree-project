from langchain_core.messages import AIMessage
from app.engine.agents.langgraph.src.agent.state import KeywordState
from app.services.keyword_service import keyword_service

import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ==========================================
# Functions
# ==========================================
async def _get_feedback(state: KeywordState) -> str:
    history = state.get("quiz_history", [])
    if not history:
        return "학습 기록이 없습니다."
        
    # 히스토리를 실제 대화형(대화 맥락)으로 포맷팅
    history_conversation = []
    for idx, item in enumerate(history):
        level = item.get('level', 0)
        q = item.get('question_text', '')
        user_ans = item.get('user_answer', '')
        model_ans = item.get('model_answer', '') # agent_quiz.py 에서는 model_answer 로 저장
        grade = item.get('grade', '')
        
        history_conversation.append(f"--- [Turn {idx+1} | Level {level}] ---")
        history_conversation.append(f"🤖 Tutor: {q}")
        history_conversation.append(f"👤 User: {user_ans}")
        history_conversation.append(f"💡 Result: {grade} (Model Answer: {model_ans})\n")
        
    history_text = "\n".join(history_conversation)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
            """
            # Role
            You are a friendly and professional AI Learning Tutor.
            Your task is to review the user's complete quiz session history and write a comprehensive, short feedback report.

            # Instructions
            1. Praise the concepts the user understood well.
            2. If there are incorrect answers, analyze what the user misunderstood and gently correct them.
            3. Keep the feedback concise, around 3 to 4 sentences in total.
            4. Do not use Markdown or special formatting. Write it naturally in plain text.

            # Language Requirement
            The final output MUST be written entirely in warm, natural Korean (한국어).

            # Quiz History Context
            <quiz_history>
            {history}
            </quiz_history>
            """
        ), 
        ("human", 
            "Based on my quiz history provided in the context, please give me a short, comprehensive feedback."
        ),
    ])

    llm = ChatOpenAI(
        model="gpt-4.1", 
        temperature=0.3, 
        api_key=os.getenv("OPENAI_API_KEY")
    )
    parser = StrOutputParser()

    feedback_chain = prompt | llm | parser
    
    try:
        feedback = await feedback_chain.ainvoke({"history": history_text})
        return feedback
    except Exception as e:
        print(f"Feedback generation error: {e}")
        return "퀴즈 결과를 바탕으로 학습을 잘 마무리하셨습니다. 수고하셨습니다."

# ==========================================
# Nodes
# ==========================================
async def report_star_node(state: KeywordState):
    """
    [Assessment Phase] Reports the evaluation result to the user. And Update user's star.
    """
    user_id = state.get("user_id", "test_user@ai-techtree.com")
    keyword = state.get("keyword", "Unknown")
    quiz_count = state.get("quiz_count", 0)
    quiz_pass_count = state.get("quiz_pass_count", 0)
    level = state.get("level", 0)
    
    # 별점 산정 로직: 레벨에 비례하여 최대 3개 (최하 1개 보장, 아예 못맞췄으면 0개)
    earned_star = 0
    is_passed = False
    
    if quiz_pass_count > 0:
        is_passed = True
        earned_star = max(1, min(level, 3))
    
    # DB 업데이트
    if keyword != "Unknown":
        await keyword_service.update_user_star(
            user_id=user_id,
            keyword_key=keyword,
            result={
                "is_passed": is_passed,
                "star": earned_star,
                "score": quiz_pass_count * 10 
            }
        )
    feedback = await _get_feedback(state)
    
    # 피드백 메시지 생성
    stars_str = "⭐" * earned_star + "☆" * (3 - earned_star)
    report_msg = (
        f"### 📊 학습 리포트\n"
        f"- **키워드**: {keyword}\n"
        f"- **정답 수**: {quiz_pass_count} / {quiz_count}\n"
        f"- **도달 레벨**: Level {level}\n"
        f"- **획득 별점**: {stars_str}\n\n"
        f"- **종합 피드백**: \n {feedback}\n\n"
        f"수고하셨습니다! 다음 학습을 시작하려면 새로운 키워드를 입력하거나 '추천'을 요청해주세요."
    )
    
    # 퀴즈 종료 시 관련 진행 상태 및 횟수 카운터 초기화
    return {
        "messages": [AIMessage(content=report_msg)],
        "keyword": None,
        "keyword_data": None,
        "current_question": None,
        "quiz_in_progress": False,
        "quiz_count": 0,
        "quiz_pass_count": 0,
        "level": 0,
        "quiz_history": []
    }
    