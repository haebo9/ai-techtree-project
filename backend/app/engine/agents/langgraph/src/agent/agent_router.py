from typing import Literal, Optional
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# ==========================================
# Router Schema
# ==========================================
class KeywordRouterOutput(BaseModel):
    """
    User intent classification for Keyword-based learning flow.
    """
    intent: Literal["KEYWORD_SEARCH", "ANSWER", "NAVIGATION", "CHIT_CHAT"] = Field(
        ..., description="Classified intent: KEYWORD_SEARCH, ANSWER, NAVIGATION, CHIT_CHAT"
    )
    keyword: Optional[str] = Field(
        None, description="Extracted keyword if intent is KEYWORD_SEARCH (e.g., 'BFS', 'Docker')"
    )
    reasoning: str = Field(..., description="Reason for classification")

# ==========================================
# Prompt Definition
# ==========================================
ROUTER_SYSTEM_PROMPT = """
You are the 'Router' for an AI TechTree Learning Agent. 
Your goal is to direct the user based on their input in a Keyword-Driven Learning Session.

[Context]
- Current Keyword: {current_keyword} (The concept currently being discussed/learned)
- Last System Action: {last_action} (e.g., 'EXPLAINED', 'ASKED_QUESTION', 'RECOMMENDED')

[Intent Classification Rules]
1. **KEYWORD_SEARCH**: 
   - User explicitly mentions a topic, concept, or technology they want to learn.
   - Examples: "BFS", "Tell me about React", "Docker containers", "What is a heap?"
   - Action: Set 'keyword' field to the extracted technical term.

2. **ANSWER**: 
   - User is responding to a question asked by the system.
   - Examples: "It is a LIFO structure", "I don't know", "Option 3", "2.5"
   - Condition: Likely if Last System Action was 'ASKED_QUESTION'.

3. **NAVIGATION**: 
   - User asks for recommendations, next steps, or related topics *without* specifying a name.
   - Examples: "Next", "What should I learn next?", "Recommend related topics", "Pass"

4. **CHIT_CHAT**: 
   - Greetings, general conversation, or off-topic queries.
   - Examples: "Hi", "Hello", "Who are you?", "Thanks"

[Output Format]
Return a JSON object conforming to the KeywordRouterOutput schema.
"""

router_prompt = ChatPromptTemplate.from_messages([
    ("system", ROUTER_SYSTEM_PROMPT),
    ("human", "{user_input}")
])

# ==========================================
# Model Setup
# ==========================================
api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0.0,
    api_key=api_key
)

router_chain = router_prompt | llm | JsonOutputParser(pydantic_object=KeywordRouterOutput)

# ==========================================
# Execution Function
# ==========================================
async def route_keyword_intent(user_input: str, current_keyword: str = "None", last_action: str = "None") -> dict:
    """
    Analyzes user input to determine the next step in the keyword learning graph.
    """
    try:
        result = await router_chain.ainvoke({
            "user_input": user_input,
            "current_keyword": current_keyword,
            "last_action": last_action
        })
        return result
    except Exception as e:
        print(f"⚠️ [KeywordRouter] Error: {e}")
        # Fallback to CHIT_CHAT if parsing fails
        return {"intent": "CHIT_CHAT", "keyword": None, "reasoning": "Error Fallback"}
