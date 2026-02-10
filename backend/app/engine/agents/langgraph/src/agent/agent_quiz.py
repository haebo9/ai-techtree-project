from typing import List
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# ==========================================
# 1. 문제 데이터 구조 (Schema)
# ==========================================


KEYWORD_QUESTION_PROMPT = """
You are an expert Interviewer.
Create a targeted technical interview question about the keyword: "{keyword}".
Use the provided context to ensure the question is relevant.

[Context]
Definition: {definition}

[Requirements]
1. Generate ONE high-quality question that test understanding of this specific concept.
2. The question should be suitable for a {level} learner.
3. Provide a clear model answer and evaluation criteria.

Output JSON format:
{format_instructions}
"""

keyword_q_prompt = ChatPromptTemplate.from_messages([
    ("system", KEYWORD_QUESTION_PROMPT),
    ("human", "Generate a question for: {keyword}")
])

keyword_chain = keyword_q_prompt | llm | parser

# LCEL 체인 구성
class GeneratedQuestion(BaseModel):
    """생성된 단일 면접 질문 구조"""
    skill: Optional[str] = Field(description="대상 기술 스택 (예: Python)")
    topic: Optional[str] = Field(description="세부 주제 (예: Generator)")
    level: str = Field(description="난이도 (Basic, Intermediate, Advanced)")
    question_text: str = Field(description="면접 질문 본문")
    model_answer: str = Field(description="질문에 대한 모범 답안")
    evaluation_criteria: List[str] = Field(description="채점 시 확인해야 할 핵심 키워드 3~5개")

class QuestionList(BaseModel):
    """질문 리스트 (LLM 출력 파싱용)"""
    questions: List[GeneratedQuestion] = Field(description="생성된 면접 질문 목록")

# ==========================================
# 2. 모델 및 파서 설정
# ==========================================
api_key = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(
    model="gpt-4o", 
    temperature=0.7, 
    api_key=api_key
)

parser = PydanticOutputParser(pydantic_object=QuestionList)

async def generate_keyword_questions(keyword: str, definition: str, level: str = "Intermediate") -> List[dict]:
    """
    Generates a question specifically targeting the given keyword and context.
    
    Returns:
        List[dict]: A list containing one question dictionary.
    """
    try:
        result = await keyword_chain.ainvoke({
            "keyword": keyword,
            "definition": definition,
            "level": level,
            "format_instructions": parser.get_format_instructions()
        })
        # Override fields to be keyword-specific if needed
        questions = [q.model_dump() for q in result.questions]
        for q in questions:
            q['topic'] = keyword # Ensure topic matches keyword
            q['skill'] = "KeywordMastery" 
        return questions
        
    except Exception as e:
        print(f"⚠️ [QAMaker] Error generating keyword question: {e}")
        return []
