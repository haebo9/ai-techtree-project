from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.engine.graphs.state import KeywordState
from app.services.keyword_service import keyword_service
from app.core.llm import get_llm
from app.core.logger import get_logger
from app.engine.prompts.report_prompts import REPORT_SYSTEM_PROMPT, REPORT_HUMAN_PROMPT

logger = get_logger("agent_report")

# Initialize LLM and Prompt globally for reuse
llm = get_llm(temperature=0.3)
parser = StrOutputParser()
report_prompt = ChatPromptTemplate.from_messages([
    ("system", REPORT_SYSTEM_PROMPT), 
    ("human", REPORT_HUMAN_PROMPT),
])
feedback_chain = report_prompt | llm | parser

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
    
    try:
        feedback = await feedback_chain.ainvoke({"history": history_text})
        return feedback
    except Exception as e:
        logger.error(f"Feedback generation error: {e}", exc_info=True)
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
    
    # 별점 산정 로직: 각 레벨별로 'perfect' 판정을 받은 가장 높은 레벨을 별점으로 산정
    earned_star = 0
    is_passed = False
    
    history = state.get("quiz_history", [])
    for item in history:
        item_grade = item.get("grade", "")
        item_level = int(item.get("level", 0))
        
        # 부분 정답(pass) 이상이면 일단 통과(is_passed=True)로 간주할 수는 있음
        if item_grade in ["pass", "perfect"]:
            is_passed = True
        
        # 단, 실제 별점(Star) 획득은 해당 레벨을 'perfect'로 맞췄을 때만 인정 (최대 3점)
        if item_grade == "perfect":
            earned_star = max(earned_star, item_level)
            
    earned_star = min(earned_star, 3) # 안전장치: 최대 3별 유지
    
    # DB 업데이트
    is_new_star = False
    if keyword != "Unknown":
        _, is_new_star = await keyword_service.update_user_star(
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
    new_badge = " *(NEW!)*" if is_new_star else ""
    report_msg = (
        f"### 📊 학습 리포트\n"
        f"- **키워드**: {keyword}\n"
        f"- **정답 수**: {quiz_pass_count} / {quiz_count}\n"
        f"- **도달 레벨**: Level {level}\n"
        f"- **획득 별점**: {stars_str}{new_badge}\n\n"
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