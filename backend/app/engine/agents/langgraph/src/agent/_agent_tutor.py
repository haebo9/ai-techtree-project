from typing import List
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# ==========================================
# Schema
# ==========================================
class KeywordContent(BaseModel):
    """
    Content generated for a specific keyword.
    """
    keyword: str = Field(description="The keyword being explained")
    definition: str = Field(description="A clear, concise definition (1-2 sentences).")
    summary: str = Field(description="A detailed explanation or summary for a learner (3-5 sentences).")
    core_concepts: List[str] = Field(description="Key concepts or terms associated with this keyword.")
    related_keywords: List[str] = Field(description="List of 3-5 semantically related keywords for further learning.")

# ==========================================
# Prompt & Chain
# ==========================================
TUTOR_SYSTEM_PROMPT = """
    You are an expert AI Tech Tutor. 
    Your goal is to explain technical concepts clearly and concisely to a learner.

    [Instructions]
    1. Definition: Provide a precise, academic definition.
    2. Summary: Explain it simply, using analogies if helpful.
    3. Core Concepts: distinct terms that are crucial to understanding this keyword.
    4. Related Keywords: Suggest 3-5 keywords that are semantically close or natural next steps.

    [Output Format]
    Return a JSON object conforming to the KeywordContent schema.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", TUTOR_SYSTEM_PROMPT),
    ("human", "Explain the keyword: {keyword}")
])

api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o", temperature=0.5, api_key=api_key)
parser = PydanticOutputParser(pydantic_object=KeywordContent)

tutor_chain = prompt | llm | parser

# ==========================================
# Execution Function
# ==========================================
async def explain_keyword(keyword: str) -> dict:
    """
    Generates educational content for a given keyword.
    """
    try:
        result = await tutor_chain.ainvoke({"keyword": keyword, "format_instructions": parser.get_format_instructions()})
        return result.model_dump()
    except Exception as e:
        print(f"⚠️ [Tutor] Error explaining keyword: {e}")
        return {
            "keyword": keyword,
            "definition": "Definition unavailable.",
            "summary": "Could not generate content at this time.",
            "core_concepts": [],
            "related_keywords": []
        }
