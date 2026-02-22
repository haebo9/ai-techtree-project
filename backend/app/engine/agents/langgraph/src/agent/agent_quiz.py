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

llm = ChatOpenAI(model="gpt-4o", temperature=0.5, api_key=os.getenv("OPENAI_API_KEY"))
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
    You are an expert AI Tech Tutor.
    Generate a NEW, challenging quiz question for the given keyword.
    
    [Context]
    Keyword: {keyword}
    
    [Instructions]
    1. Create a multiple-choice or short-answer question.
    2. Provide the correct answer and a brief explanation.
    3. Ensure it's different from potentially previous questions if possible (State depends on LLM randomness).
    
    [Language]
    - Question/Answer in Korean.
    
    {format_instructions}
"""

quiz_prompt = ChatPromptTemplate.from_messages([
    ("system", QUIZ_SYSTEM_PROMPT),
    ("human", "Generate a quiz for: {keyword}")
]).partial(format_instructions=quiz_parser.get_format_instructions())

quiz_chain = quiz_prompt | llm | quiz_parser

async def generate_only_quiz(keyword: str) -> dict:
    try:
        result = await quiz_chain.ainvoke({"keyword": keyword})
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
    if keyword:
        question = await generate_only_quiz(keyword)
    
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
        "messages": [AIMessage(content=f"### 🎯 현재 키워드: **{keyword}**\n\n**Q. {question['question_text']}**{options_text}")],
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
    
    # 1. 정답 확인 스키마 정의 (별점 제거)
    class CheckResult(BaseModel):
        is_correct: bool = Field(description="True if the answer is correct contextually, False otherwise.")
        feedback: str = Field(description="Brief feedback explaining why it's correct or incorrect.")

    # 2. 평가 체인 구성
    check_prompt = ChatPromptTemplate.from_messages([
        ("system", """
        You are a strict Grader. Compare the user's answer with the model answer.
        
        [Question]
        {question}
        
        [Model Answer]
        {model_answer}
        
        [User Answer]
        {user_answer}
        
        Task:
        1. Determine if the user's answer is correct considering the model answer.
        2. Provide brief feedback in Korean.
        """),
        ("human", "{user_answer}")
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
        
        # 3. 결과 메시지
        msg = AIMessage(content=f"**판정**: {'✅ 정답' if result.is_correct else '❌ 오답'}\n{result.feedback}")
        
        # 4. 다음 단계 결정 (Pass/Fail)
        if result.is_correct:
            # 정답 -> 다음 퀴즈 (Pass)
            # current_question을 비워서 generate_quiz_node에서 새로 생성하게 함
            return {
                "pass_fail": "pass",
                "messages": [msg],
                "current_question": None, # Clear to trigger new quiz
                "quiz_in_progress": True # Keep active for next quiz loop
            }
        else:
            # 오답 -> 결과 리포트 (Fail)
            return {
                "evaluation_result": {"is_passed": False, "feedback": result.feedback},
                "pass_fail": "fail",
                "messages": [msg],
                "quiz_in_progress": False # End quiz mode
            }
        
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
    
    # 퀴즈 종료 시 관련 진행 상태 초기화
    return {
        "messages": [AIMessage(content="## Report")],
        "keyword": None,
        "keyword_data": None,
        "current_question": None,
        "quiz_in_progress": False
    }

