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
# Execution Function
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
# Nodes
# ==========================================
from langchain_core.messages import AIMessage
from app.engine.agents.langgraph.src.agent.state import KeywordState

# 퀴즈 생성 노드 : 키워드를 기반으로 퀴즈 생성
async def generate_quiz_node(state: KeywordState):
    """
    [Assessment Phase] Generates a question based on valid content.
    """
    # 이미 search_keyword_node에서 생성된 퀴즈를 가져옴
    question = state.get("current_question")
    
    if not question or not question.get("question_text"):
         return {"messages": [AIMessage(content="Could not generate a quiz at this moment.")]}
    
    # 퀴즈 출력 메시지 구성
    options_text = ""
    if question.get("options"):
        options_text = "\n" + "\n".join([f"- {opt}" for opt in question["options"]])
         
    return {
        "messages": [AIMessage(content=f"**Q. {question['question_text']}**{options_text}")]
    }

async def evaluate_quiz_node(state: KeywordState):
    """
    [Assessment Phase] Evaluates the user's answer. Simple evaluation(Correct/Incorrect/Stop).
    if Stop -> report_star_node
    else -> generate_quiz_node

    Input: 
        current_question: dict
        messages: List[BaseMessage]
    return: 
        evaluation_result: str
    """
    # TODO: Implement evaluation logic
    return {"pass_fail": "fail", "messages": [AIMessage(content="Evaluation logic not implemented yet.")]}

async def report_star_node(state: KeywordState):
    """
    [Assessment Phase] Reports the evaluation result to the user. And Update user's star.
    """
    # TODO: Implement reporting logic
    return {"messages": [AIMessage(content="Reporting logic not implemented yet.")]}

