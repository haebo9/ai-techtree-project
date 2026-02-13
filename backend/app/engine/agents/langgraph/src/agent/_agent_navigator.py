from typing import List
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# ==========================================
# Schema
# ==========================================
class RecommendationResult(BaseModel):
    """
    List of recommended keywords for the user to explore next.
    """
    recommendations: List[str] = Field(description="List of 3-5 recommended keywords.")
    reasoning: str = Field(description="Brief explanation of why these were recommended.")

# ==========================================
# Prompt & Chain
# ==========================================
NAVIGATOR_SYSTEM_PROMPT = """
You are an expert AI Learning Navigator.
Your goal is to recommend the best next steps for a learner based on their current context.

[Context]
- Current Keyword: {keyword}
- Related Keywords (from content): {related_keywords}

[Instructions]
1. Analyze the 'current keyword' and its 'related keywords'.
2. Select or generate 3-5 high-quality next topics.
3. Prioritize concepts that logically follow the current one (e.g., if 'Docker', suggest 'Images', 'Containers', 'Compose').
4. Provide a brief reasoning.

[Output Format]
Return a JSON object conforming to the RecommendationResult schema.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", NAVIGATOR_SYSTEM_PROMPT),
    ("human", "Recommend next steps for: {keyword}. Related: {related_keywords}")
])

api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o", temperature=0.5, api_key=api_key)
parser = PydanticOutputParser(pydantic_object=RecommendationResult)

navigator_chain = prompt | llm | parser

# ==========================================
# Execution Function
# ==========================================
async def recommend_next_keywords(keyword: str, related_keywords: List[str]) -> dict:
    """
    Generates recommendations for the next learning steps.
    """
    try:
        result = await navigator_chain.ainvoke({
            "keyword": keyword, 
            "related_keywords": ", ".join(related_keywords),
            "format_instructions": parser.get_format_instructions()
        })
        return result.model_dump()
    except Exception as e:
        print(f"⚠️ [Navigator] Error recommending keywords: {e}")
        return {
            "recommendations": related_keywords[:5], # Fallback to existing related keywords
            "reasoning": "Fallback based on static relation."
        }
