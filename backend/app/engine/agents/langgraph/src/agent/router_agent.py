from typing import Literal, Optional, TypedDict
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# 1. Router Output Schema
class RouterOutput(BaseModel):
    intent: Literal["ANSWER", "NEXT_QUESTION", "CHANGE_TOPIC", "CONSULT", "QUIT"] = Field(
        ..., description="The user's primary intent."
    )
    topic: Optional[str] = Field(
        None, description="If intent is CHANGE_TOPIC, specity the new topic (e.g., 'Python', 'React'). Otherwise null."
    )
    reasoning: str = Field(..., description="Brief reason for this classification.")

# 2. Prompt
ROUTER_SYSTEM_PROMPT = """
    You are the 'Router' of an AI Interviewer System.
    Your job is to analyze the user's latest input and conversation context to decide the next action.

    [Context]
    - Current Topic: {current_topic}
    - Last Question: {last_question}

    [Intents]
    - ANSWER: The user is attempting to answer the interview question. (e.g., "It is a mechanism...", "I don't know", Code snippets)
    - NEXT_QUESTION: The user wants to skip or simply asks for the next problem. (e.g., "Next", "Pass", "Give me another one")
    - CHANGE_TOPIC: The user explicitly wants to change the subject. (e.g., "Let's do Java", "Can we ask about DB?")
    - CONSULT: The user is asking general questions, seeking advice, or just chatting, unrelated to the specific interview question. (e.g., "What should I study?", "Hi")
    - QUIT: The user wants to end the session. (e.g., "Stop", "Bye", "End")

    [Instruction]
    - If the user provides an answer (even if wrong or short), classify as ANSWER.
    - If the user just says "Start" or "Begin" at the very beginning, classify as CHANGE_TOPIC (if topic implied) or NEXT_QUESTION (to start).
    - Output JSON strictly matching the schema.
    """

router_prompt = ChatPromptTemplate.from_messages([
    ("system", ROUTER_SYSTEM_PROMPT),
    ("human", "{user_input}")
])

# 3. Chain
# NOTE: Removed dependency on settings.OPENAI_API_KEY, using os.getenv instead
api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-4o-mini", # Fast model for routing
    temperature=0.0,
    api_key=api_key
)

router_chain = router_prompt | llm | JsonOutputParser(pydantic_object=RouterOutput)

async def route_user_input(user_input: str, current_topic: str = "General", last_question: str = "") -> dict:
    """
    Analyzes user input to determine the next step in the interview graph.
    """
    try:
        result = await router_chain.ainvoke({
            "user_input": user_input,
            "current_topic": current_topic,
            "last_question": last_question
        })
        return result
    except Exception as e:
        # Fallback in case of parsing error
        print(f"Router Error: {e}")
        return {"intent": "CONSULT", "topic": None, "reasoning": "Error fallback"}
