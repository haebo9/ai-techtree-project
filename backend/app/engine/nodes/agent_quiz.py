import re
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import AIMessage

# Project Utilities
from app.core.llm import get_llm
from app.core.logger import get_logger
from app.engine.prompts.quiz_prompts import (
    INTEGRATED_SYSTEM_PROMPT,
    EXPLANATION_SYSTEM_PROMPT,
    QUIZ_SYSTEM_PROMPT,
    CHECK_RESULT_SYSTEM_PROMPT,
    CHECK_RESULT_HUMAN_PROMPT
)
from app.engine.graphs.state import KeywordState
from app.engine.nodes.schemas_quiz import (
    KeywordAndQuiz,
    ExplanationGeneration,
    QuizGeneration,
    CheckResult
)

logger = get_logger("agent_quiz")
llm = get_llm()

# ==========================================
# Parsers & Prompts Configuration
# ==========================================
parser = PydanticOutputParser(pydantic_object=KeywordAndQuiz)
prompt = ChatPromptTemplate.from_messages([
    ("system", INTEGRATED_SYSTEM_PROMPT),
    ("human", "Teach me about: {keyword}")
]).partial(format_instructions=parser.get_format_instructions())

chain = prompt | llm | parser

explanation_parser = PydanticOutputParser(pydantic_object=ExplanationGeneration)
explanation_prompt = ChatPromptTemplate.from_messages([
    ("system", EXPLANATION_SYSTEM_PROMPT),
    ("human", "Teach me about: {keyword}")
]).partial(format_instructions=explanation_parser.get_format_instructions())

explanation_chain = explanation_prompt | llm | explanation_parser

quiz_parser = PydanticOutputParser(pydantic_object=QuizGeneration)
quiz_prompt = ChatPromptTemplate.from_messages([
    ("system", QUIZ_SYSTEM_PROMPT),
    ("human", "Generate a quiz for: {keyword}")
]).partial(format_instructions=quiz_parser.get_format_instructions())

quiz_chain = quiz_prompt | llm | quiz_parser

check_prompt = ChatPromptTemplate.from_messages([
    ("system", CHECK_RESULT_SYSTEM_PROMPT),
    ("human", CHECK_RESULT_HUMAN_PROMPT)
])
llm_with_structure = llm.with_structured_output(CheckResult)
check_chain = check_prompt | llm_with_structure


# ==========================================
# Explanation Only Generation
# ==========================================
async def generate_explanation_only(keyword: str) -> dict:
    """
    Generates explanation only (No Quiz).
    """
    try:
        result = await explanation_chain.ainvoke({"keyword": keyword})
        return result.model_dump()
    except Exception as e:
        logger.error(f"⚠️ [ExplanationAgent] Error: {e}", exc_info=True)
        return {
            "keyword": keyword,
            "definition": "Content unavailable.",
            "summary": "Could not generate content.",
            "core_concepts": []
        }

# ==========================================
# Execution Function (Legacy Combined)
# ==========================================
async def generate_quiz_and_explanation(keyword: str) -> dict:
    """
    Generates both explanation and a quiz for a given keyword in one go.
    """
    try:
        result = await chain.ainvoke({"keyword": keyword})
        return result.model_dump()
    except Exception as e:
        logger.error(f"⚠️ [IntegratedAgent] Error: {e}", exc_info=True)
        return {
            "keyword": keyword,
            "definition": "Content unavailable.",
            "summary": "Could not generate content.",
            "core_concepts": [],
            "quiz_question": "Quiz generation failed.",
            "quiz_options": [],
            "quiz_answer": ""
        }

# ==========================================
# Quiz Only Generation
# ==========================================
async def generate_only_quiz(keyword: str, level: int, quiz_history: List[dict] = None) -> dict:
    level_map = {
        0: "Very Easy (Matching a term to its corresponding concept)",
        1: "Easy (Providing a brief explanation of a term)",
        2: "Medium (Applying concepts and comparing them with other concepts)",
        3: "Hard (In-depth concepts, performance optimization, and operating principles)"
    }
    level_desc = level_map.get(level, level_map[0])
    
    history_text = "No previous questions."
    if quiz_history:
        history_lines = []
        for idx, log in enumerate(quiz_history, 1):
            history_lines.append(f"[{idx}] Level {log.get('level')} | Q: {log.get('question_text')} | Grade: {log.get('grade')}")
        history_text = "\n".join(history_lines)
    
    try:
        result = await quiz_chain.ainvoke({
            "keyword": keyword,
            "level": level_desc,
            "quiz_history_context": history_text
        })
        return {
            "question_text": result.quiz_question,
            "options": result.quiz_options,
            "answer": result.quiz_answer
        }
    except Exception as e:
        logger.error(f"Quiz Gen Error: {e}", exc_info=True)
        return None

# ==========================================
# Nodes
# ==========================================
async def generate_quiz_node(state: KeywordState):
    """
    [Assessment Phase] Generates a question based on valid content.
    """
    
    # 1. 퀴즈 새로 생성
    keyword = state.get("keyword")
    level = state.get("level", 0)  # Use level 0 as default if not defined
    quiz_history = state.get("quiz_history", [])
    
    question = None
    if keyword:
        question = await generate_only_quiz(keyword, level, quiz_history)
    
    if not question or not question.get("question_text"):
        # 키워드 자체가 없어서 실패한 경우 에러 메시지를 띄우지 않고 조용히 종료 (search_keyword_node에서 이미 안내함)
        if not keyword:
            return {"user_intent": "FINISH"}
        return {
            "messages": [AIMessage(content="Could not generate a quiz at this moment.")],
            "user_intent": "FINISH"
        }
    
    # 2. 퀴즈 출력 메시지 구성
    options_text = ""
    if question.get("options"):
        formatted_options = []
        for i, opt in enumerate(question["options"], 1):
            # LLM이 "1. 정답" 등 이미 번호를 매긴 경우를 대비하여 앞의 번호/기호 제거
            clean_opt = re.sub(r'^([0-9]+|[a-zA-Z])[\.\)]\s*', '', opt.strip())
            formatted_options.append(f"{i}. {clean_opt}")
        options_text = "\n\n" + "\n".join(formatted_options)
         
    return {
        "current_question": question, # Ensure state is updated/restored
        "messages": [AIMessage(content=f"### 🎯 주제: **{keyword}** (Level: {level})\n\n**Q. {question['question_text']}**{options_text}")],
        "quiz_in_progress": True, # 퀴즈 모드 활성화
        "user_intent": "FINISH",
        "hint_used": False # 새 퀴즈 생성 시 힌트 사용 여부 초기화
    }

async def answer_quiz_node(state: KeywordState):
    """
    [Assessment Phase] Evaluates the user's answer (Correctness Check only).
    """
    current_q = state.get("current_question")
    messages = state.get("messages")
    user_answer = messages[-1].content
    
    if not current_q:
        return {"pass_fail": "fail", "messages": [AIMessage(content="No active quiz found.")]}
        
    model_answer = current_q.get("answer", "")
    question_text = current_q.get("question_text", "")
    
    try:
        result: CheckResult = await check_chain.ainvoke({
            "question": question_text,
            "model_answer": model_answer,
            "user_answer": user_answer
        })
        
        # 3. 횟수 업데이트 및 판정
        quiz_count = state.get("quiz_count", 0) + 1
        quiz_pass_count = state.get("quiz_pass_count", 0)
        quiz_max_count = state.get("quiz_max_count", 8)
        level = state.get("level", 0)
        
        pass_fail_status = "pass" if result.grade in ["pass", "perfect"] else "fail"
        
        if result.grade in ["pass", "perfect"]:
            quiz_pass_count += 1
            # 확실히 맞은 경우(perfect)에만 레벨 상승
            if result.grade == "perfect" and level < 3:
                level += 1
                
        # 판정 텍스트 결정
        if result.grade == "perfect":
            grade_text = "✅ 정답"
        elif result.grade == "pass":
            grade_text = "⚠️ 부분 정답"
        else:
            grade_text = "❌ 오답"
            
        # 메시지에 현재 진행도를 항상 동일하게 표시
        msg_content = f"**판정**: {grade_text}\n\n{result.feedback}\n\n**[정답]** {result.correct_answer}\n\n*(진행도: {quiz_count}/{quiz_max_count})*"
        msg = AIMessage(content=msg_content)
        
        # 이전 히스토리에 현재 문제와 결과 추가
        quiz_history = state.get("quiz_history", [])
        quiz_history.append({
            "question_text": question_text,
            "model_answer": model_answer,   # 문제의 모범 정답 (저장용)
            "user_answer": user_answer,     # 사용자의 원본 답변 기록 (분석/저장용, 다음 문제 출제 프롬프트에는 미포함)
            "level": state.get("level", 0), # 문제 출제 시점의 레벨
            "grade": result.grade
        })
        
        # 4. 결과 반환 (이후 라우팅은 graph.py의 quiz_routing 에서 횟수/정답여부를 바탕으로 결정)
        return_data = {
            "quiz_count": quiz_count,
            "quiz_pass_count": quiz_pass_count,
            "level": level,
            "pass_fail": pass_fail_status,
            "quiz_history": quiz_history,
            "messages": [msg],
            "current_question": None, # 새 퀴즈 생성 대비 항상 클리어
            "quiz_in_progress": True  # 기본적으로 켜둠 (report_star 노드 도달 시에만 강제 False 전환됨)
        }
        
        # 오답인 경우에만 평가 내역 상세 저장 (Report 활용)
        if result.grade == "fail":
            return_data["evaluation_result"] = {"is_passed": False, "feedback": result.feedback}
            
        return return_data
        
    except Exception as e:
        logger.error(f"Eval Error: {e}", exc_info=True)
        return {
            "pass_fail": "fail", 
            "messages": [AIMessage(content="정답 확인 중 오류가 발생했습니다.")]
        }

async def quiz_chat_node(state: KeywordState):
    """
    [Quiz Phase] Handles hint requests and general Q&A during a quiz.
    """
    from langchain_core.messages import SystemMessage
    from app.engine.nodes.tools import quiz_tools
    
    # 힌트를 이미 사용했는지 체크
    if state.get("hint_used", False):
        msg = AIMessage(content="🚫 이미 이 문제에 대한 힌트를 제공해 드렸습니다. 정답을 시도해 보세요!")
        return {"messages": [msg], "user_intent": "FINISH"}
    
    agent_llm = get_llm(temperature=0.4).bind_tools(quiz_tools)
    keyword = state.get("keyword", "알 수 없음")
    current_question = state.get("current_question")
    q_text = current_question.get("question_text") if current_question else "출제된 문제 없음"
    messages = state.get("messages", [])
    
    chat_sys_prompt = f"""당신은 실제 개발자 면접을 진행하는 기술 면접관입니다.
        현재 면접 주제(Keyword): {keyword}
        주어진 질문(Question): {q_text}

        지원자(User)가 답변을 어려워하며 힌트를 요청하거나 헤매고 있습니다.
        면접관으로서 절대 정답(핵심 단어, 코드 등)을 직접적으로 노출하지 마세요. 
        대신 지원자가 스스로 답에 도달할 수 있도록 '방향성만 제시하는 가벼운 유도 질문(Socratic Method)'을 던져야 합니다.
        
        [제약 사항]
        1. 정답을 유추할 수 있는 결정적 단어나 코드는 절대 방출 금지.
        2. 다른 비유를 들거나, 지원자가 아는 다른 기초 개념에서 출발하도록 역질문하세요.
        3. 반드시 1~2문장 이내로 짧고 간결하게 대답하세요.
        
        # Example
        User: 모르겠어 
        AI: ❗ 데이터들이 순서대로 줄을 서 있다고 생각해볼까요? 그중 원하는 순서의 데이터를 콕 집어오려면 어떤 방식을 썼는지 떠올려보세요.
        """
    agent_msgs = [SystemMessage(content=chat_sys_prompt)] + messages
    ai_response = await agent_llm.ainvoke(agent_msgs)
    
    return {"messages": [ai_response], "user_intent": "FINISH", "hint_used": True}
