from typing import List
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# ==========================================
# 1. 문제 데이터 구조 (Schema)
# ==========================================
class GeneratedQuestion(BaseModel):
    """생성된 단일 면접 질문 구조"""
    skill: str = Field(description="대상 기술 스택 (예: Python)")
    topic: str = Field(description="세부 주제 (예: Generator)")
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

# 창의적인 문제 생성을 위해 온도(Temperature)를 약간 높게 설정 (0.7)
llm = ChatOpenAI(
    model="gpt-4o", 
    temperature=0.7, 
    api_key=api_key
)

parser = PydanticOutputParser(pydantic_object=QuestionList)

# ==========================================
# 3. 프롬프트 정의 (Prompt Engineering)
# ==========================================
GENERATOR_SYSTEM_PROMPT = """
당신은 IT 기술 면접 문제 출제 위원입니다.
주어진 주제와 난이도에 맞춰 고품질의 기술 면접 문제를 {count}개 생성하세요.

[요구사항]
1. 각 문제는 서로 다른 세부 개념을 다루거나, 다른 측면(저장소, 성능, 보안 등)을 물어봐야 합니다. (중복 금지)
2. 질문은 실무적이고 깊이 있는 내용을 다뤄야 합니다.
3. 모범 답안은 핵심 개념과 예시를 포함하여 명확하게 작성하세요.
4. 평가 기준은 채점자가 답변을 보고 바로 판단할 수 있는 키워드 위주로 3~5개 작성하세요.

다음의 JSON 형식으로만 응답하세요:
{format_instructions}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", GENERATOR_SYSTEM_PROMPT),
    ("human", """
    [출제 요청]
    - 기술 스택: {skill}
    - 세부 주제: {topic}
    - 난이도: {level}
    - 문제 수: {count}개
    """),
])

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
generator_chain = prompt | llm | parser

# ==========================================
# 4. 실행 함수 (Execution Function)
# ==========================================
async def generate_questions(skill: str, topic: str, level: str = "Intermediate", count: int = 1) -> List[dict]:
    """
    조건에 맞는 기술 면접 문제를 생성합니다.
    
    Args:
        skill (str): 기술 스택 (예: Python)
        topic (str): 세부 주제 (예: GIL)
        level (str): 난이도
        count (int): 생성할 문제 수
        
    Returns:
        List[dict]: 생성된 질문들의 딕셔너리 리스트
    """
    try:
        result = await generator_chain.ainvoke({
            "skill": skill,
            "topic": topic,
            "level": level,
            "count": count,
            "format_instructions": parser.get_format_instructions()
        })
        
        # Pydantic 모델을 dict 리스트로 변환하여 반환
        return [q.model_dump() for q in result.questions]
        
    except Exception as e:
        print(f"⚠️ [QAMaker] Error generating questions: {e}")
        # 실패 시 빈 리스트 반환 (호출부에서 처리)
        return []

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
