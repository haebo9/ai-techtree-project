from typing import List, Optional
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# ==========================================
# Schema (Integrated)
# ==========================================
class KeywordAndQuiz(BaseModel):
    """
    Content generated for a specific keyword, including explanation and assessment.
    """
    keyword: str = Field(description="The keyword being explained")
    
    # Content Part (Tutor)
    definition: str = Field(description="A precise, academic definition (1-2 sentences).")
    summary: str = Field(description="A easy-to-understand summary for a learner using analogies if helpful.")
    core_concepts: List[str] = Field(description="3-5 key concepts associated with this keyword.")
    
    # Assessment Part (Quiz)
    quiz_question: str = Field(description="A single technical question to test understanding of the keyword.")
    quiz_options: Optional[List[str]] = Field(description="For multiple choice, list options. Empty if open-ended.")
    quiz_answer: str = Field(description="The correct answer and brief explanation.")

# ==========================================
# Prompt & Chain
# ==========================================
INTEGRATED_SYSTEM_PROMPT = """
    You are an expert AI Tech Tutor and Interviewer.
    Your goal is to teach a concept and immediately assess the learner's understanding.

    [Instructions]
    1. Explain the given keyword clearly (Definition & Summary).
    2. Generate ONE high-quality quiz question based on your explanation.
    3. The question should be suitable for an intermediate learner.

    [Language Requirement]
    - **MUST** provide definition, summary, quiz question, options, and answer explanation in **KOREAN (한국어)**.
    - The 'keyword' itself can be English or Korean.

    [Output Format]
    Return a JSON object conforming to the KeywordAndQuiz schema.
    {format_instructions}
"""

parser = PydanticOutputParser(pydantic_object=KeywordAndQuiz)

prompt = ChatPromptTemplate.from_messages([
    ("system", INTEGRATED_SYSTEM_PROMPT),
    ("human", "Teach me about: {keyword}")
]).partial(format_instructions=parser.get_format_instructions())

llm = ChatOpenAI(model="gpt-4.1", temperature=0.5, api_key=os.getenv("OPENAI_API_KEY"))
chain = prompt | llm | parser

# ==========================================
# Explanation Only Generation
# ==========================================
class ExplanationGeneration(BaseModel):
    """
    Content generated for a specific keyword (Tutor only, no quiz).
    """
    keyword: str = Field(description="The keyword being explained")
    definition: str = Field(description="A precise, academic definition (1-2 sentences).")
    summary: str = Field(description="A easy-to-understand summary for a learner using analogies if helpful.")
    core_concepts: List[str] = Field(description="3-5 key concepts associated with this keyword.")

explanation_parser = PydanticOutputParser(pydantic_object=ExplanationGeneration)

EXPLANATION_SYSTEM_PROMPT = """
    You are an expert AI Tech Tutor.
    Your goal is to teach a concept clearly and concisely.

    [Instructions]
    1. Explain the given keyword clearly (Definition & Summary).
    2. Provide 3-5 core concepts.
    
    [Language Requirement]
    - **MUST** provide definition and summary in **KOREAN (한국어)**.
    - The 'keyword' itself can be English or Korean.

    {format_instructions}
"""

explanation_prompt = ChatPromptTemplate.from_messages([
    ("system", EXPLANATION_SYSTEM_PROMPT),
    ("human", "Teach me about: {keyword}")
]).partial(format_instructions=explanation_parser.get_format_instructions())

explanation_chain = explanation_prompt | llm | explanation_parser

async def generate_explanation_only(keyword: str) -> dict:
    """
    Generates explanation only (No Quiz).
    """
    try:
        result = await explanation_chain.ainvoke({"keyword": keyword})
        return result.model_dump()
    except Exception as e:
        print(f"⚠️ [ExplanationAgent] Error: {e}")
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
        print(f"⚠️ [IntegratedAgent] Error: {e}")
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
class QuizGeneration(BaseModel):
    quiz_question: str = Field(description="A single technical question to test understanding of the keyword.")
    quiz_options: Optional[List[str]] = Field(description="For multiple choice, list options. Empty if open-ended.")
    quiz_answer: str = Field(description="The correct answer and brief explanation.")

quiz_parser = PydanticOutputParser(pydantic_object=QuizGeneration)

QUIZ_SYSTEM_PROMPT = """
    This is a Company Tech Interview Question Generator.
    Generate a NEW, challenging quiz question for the given keyword.
    
    # Context
    Keyword: {keyword}
    Level: {level}
    
    # Previous Quiz History
    To avoid repeating the same questions and to potentially create linked or more advanced questions, here is the history of questions already asked in this session:
    {quiz_history_context}
    
    # Instructions
    1. Create a short-answer question.
    2. Provide the correct answer and a brief explanation.
    3. Ensure the new question is DIFFERENT from the Previous Quiz History.
    
    # Language
    - Question/Answer in Korean.
    
    {format_instructions}
"""

quiz_prompt = ChatPromptTemplate.from_messages([
    ("system", QUIZ_SYSTEM_PROMPT),
    ("human", "Generate a quiz for: {keyword}")
]).partial(format_instructions=quiz_parser.get_format_instructions())

quiz_chain = quiz_prompt | llm | quiz_parser

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
            history_lines.append(f"[{idx}] Level: {log.get('level')} | Q: {log.get('question_text')} | Grade: {log.get('grade')}")
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
        print(f"Quiz Gen Error: {e}")
        return None

# ==========================================
# Nodes
# ==========================================
from langchain_core.messages import AIMessage
from app.engine.agents.langgraph.src.agent.state import KeywordState

# 퀴즈 생성 노드 : 키워드를 기반으로 퀴즈 생성
async def generate_quiz_node(state: KeywordState):
    """
    [Assessment Phase] Generates a question based on valid content.
    """
    
    # 1. 퀴즈 새로 생성
    keyword = state.get("keyword")
    level = state.get("level", 0)  # Use level 0 as default if not defined
    quiz_history = state.get("quiz_history", [])
    if keyword:
        question = await generate_only_quiz(keyword, level, quiz_history)
    
    if not question or not question.get("question_text"):
         return {"messages": [AIMessage(content="Could not generate a quiz at this moment.")]}
    
    # 2. 퀴즈 출력 메시지 구성
    options_text = ""
    if question.get("options"):
        import re
        formatted_options = []
        for i, opt in enumerate(question["options"], 1):
            # LLM이 "1. 정답" 등 이미 번호를 매긴 경우를 대비하여 앞의 번호/기호 제거
            clean_opt = re.sub(r'^([0-9]+|[a-zA-Z])[\.\)]\s*', '', opt.strip())
            formatted_options.append(f"{i}. {clean_opt}")
        options_text = "\n\n" + "\n".join(formatted_options)
         
    return {
        "current_question": question, # Ensure state is updated/restored
        "messages": [AIMessage(content=f"### 🎯 주제: **{keyword}** (Level: {level})\n\n**Q. {question['question_text']}**{options_text}")],
        "quiz_in_progress": True # 퀴즈 모드 활성화
    }

async def answer_quiz_node(state: KeywordState):
    """
    [Assessment Phase] Evaluates the user's answer (Correctness Check only).
    """
    # Remove local import, use global pydantic import
    # from langchain_core.pydantic_v1 import BaseModel, Field as PydanticField
    
    current_q = state.get("current_question")
    messages = state.get("messages")
    user_answer = messages[-1].content
    
    if not current_q:
        return {"pass_fail": "fail", "messages": [AIMessage(content="No active quiz found.")]}
        
    model_answer = current_q.get("answer", "")
    question_text = current_q.get("question_text", "")
    
    # 1. 정답 확인 스키마 정의 
    from typing import Literal
    class CheckResult(BaseModel):
        grade: Literal["fail", "pass", "perfect"] = Field(description="fail for incorrect, pass for partially correct/acceptable, perfect for completely correct.")
        feedback: str = Field(description="Brief feedback explaining the grade in Korean. And explain why it is correct or incorrect.")
        correct_answer: str = Field(description="The correct answer based on the model answer.")

    # 2. 평가 체인 구성
    check_prompt = ChatPromptTemplate.from_messages([
        ("system", """
            # Role and Objective
            You are a fair, intelligent, and flexible Grader. Your objective is to evaluate the user's answer based on the core semantic meaning of the model answer, rather than requiring an exact word-for-word match.

            # Instructions
            - Focus strictly on the **core meaning and concepts**.
            - Actively accept synonyms, paraphrasing, and different sentence structures.
            - Grade the user's answer into one of three categories:
            - "perfect": The user clearly understands the core concept and provides a semantically equivalent answer, even if phrased differently.
            - "pass": The answer is partially correct, capturing the general idea but lacking important details or having minor inaccuracies.
            - "fail": The answer is fundamentally incorrect, misses the core points, or contradicts the model answer.

            # Reasoning Steps
            Follow these steps strictly before making a final decision:
            1. Model Answer Analysis: Identify the essential keywords and core logic required for a correct answer.
            2. User Answer Analysis: Extract the underlying meaning and logic from the user's response.
            3. Semantic Comparison: Compare the user's logic against the core logic of the model answer. Do not penalize for different vocabulary if the meaning is intact.
            4. Decision: Based on the comparison, decide the final grade and formulate constructive feedback.

            # Output Format
            You must return the result in strictly valid JSON format with the following keys:
            - "reasoning": Your step-by-step thinking process based on the Reasoning Steps (in Korean).
            - "grade": "perfect", "pass", or "fail".
            - "feedback": Brief, constructive feedback in Korean.
            - "correct_answer": The explicit correct answer in Korean.

            # Context
            <question>
            {question}
            </question>

            <model_answer>
            {model_answer}
            </model_answer>
            """),
        ("human", """
            <user_answer>
            {user_answer}
            </user_answer>

            # Final Instructions
            First, think carefully step by step following the Reasoning Steps outlined above. Then, provide the final evaluation in the requested JSON format.
            """)
    ])
    
    # Using structured output
    llm_with_structure = llm.with_structured_output(CheckResult)
    check_chain = check_prompt | llm_with_structure
    
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
            grade_text = "✅ 정답 (부분 인정)"
        else:
            grade_text = "❌ 오답"
            
        # 메시지에 현재 진행도를 항상 동일하게 표시
        msg_content = f"**판정**: {grade_text}\n\n{result.feedback}\n\n**[정답]** {result.correct_answer}\n\n*(진행도: {quiz_count}/{quiz_max_count})*"
        msg = AIMessage(content=msg_content)
        
        # 이전 히스토리에 현재 문제와 결과 추가
        quiz_history = state.get("quiz_history", [])
        quiz_history.append({
            "question_text": question_text,
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
        print(f"Eval Error: {e}")
        return {
            "pass_fail": "fail", 
            "messages": [AIMessage(content="정답 확인 중 오류가 발생했습니다.")]
        }

async def report_star_node(state: KeywordState):
    """
    [Assessment Phase] Reports the evaluation result to the user. And Update user's star.
    """
    # TODO: Implement reporting logic
    
    # 퀴즈 종료 시 관련 진행 상태 및 횟수 카운터 초기화
    return {
        "messages": [AIMessage(content="## Report")],
        "keyword": None,
        "keyword_data": None,
        "current_question": None,
        "quiz_in_progress": False,
        "quiz_count": 0,
        "quiz_pass_count": 0,
        "level": 0,
        "quiz_history": []
    }

