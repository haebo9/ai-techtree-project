from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Optional, Literal, TypedDict
from typing_extensions import Annotated
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv('.env'))

from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage

# Local Modules
from agent.agent_router import route_keyword_intent
from agent.agent_tutor import explain_keyword
from agent.agent_quiz import generate_keyword_questions
from agent.agent_evaluator import evaluate_answer # Reusing existing evaluator
from agent.agent_navigator import recommend_next_keywords
from app.services.keyword_service import keyword_service

# ==========================================
# 1. State Definition
# ==========================================
class KeywordState(TypedDict, total=False):
    """
    State for the Keyword-Driven Learning Flow.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User Context
    user_id: str
    user_db_id: str
    
    # Current Focus
    keyword: str             # The active keyword
    keyword_data: dict       # Extracted/Generated content (def, summary)
    
    # Quiz Context
    current_question: Optional[dict]
    evaluation_result: Optional[dict]
    
    # Navigation
    next_recommendations: List[str]
    user_intent: str         # From Router

# ==========================================
# 2. Nodes
# ==========================================

async def router_node(state: KeywordState):
    """
    Analyzes input to decide the next step.
    """
    messages = state["messages"]
    last_msg = messages[-1]
    
    if isinstance(last_msg, AIMessage):
        return {"user_intent": "WAIT"}
        
    user_input = last_msg.content
    curr_kw = state.get("keyword", "None")
    
    # Determine intent
    router_out = await route_keyword_intent(user_input, curr_kw)
    intent = router_out.get("intent", "CHIT_CHAT")
    extracted_kw = router_out.get("keyword")
    
    updates = {"user_intent": intent}
    if intent == "KEYWORD_SEARCH" and extracted_kw:
        updates["keyword"] = extracted_kw
        # Reset context for new keyword
        updates["keyword_data"] = {} 
        updates["current_question"] = None
        
    return updates

async def search_and_explain_node(state: KeywordState):
    """
    [Content Phase] 
    1. Searches (or generates) info for the keyword.
    2. Explains it to the user.
    """
    kw = state.get("keyword")
    if not kw:
        return {"messages": [AIMessage(content="Please specify a keyword to learn.")]}
    
    # 1. Check DB first
    kw_data_db = await keyword_service.get_keyword(kw)
    
    if kw_data_db:
        kw_data = kw_data_db
    else:
        # 2. If miss, generate content
        kw_data = await explain_keyword(kw)
        # Save newly generated keyword to DB
        await keyword_service.create_keyword(kw_data)
    
    # Construct explanation message
    
    # Construct explanation message
    msg_content = f"## 📚 Concept: {kw}\n\n" \
                  f"**Definition**: {kw_data.get('definition')}\n\n" \
                  f"**Summary**: {kw_data.get('summary')}\n\n" \
                  f"*(Preparing a quiz for you...)*"
                  
    return {
        "keyword_data": kw_data,
        "messages": [AIMessage(content=msg_content)]
    }

async def generate_quiz_node(state: KeywordState):
    """
    [Assessment Phase] Generates a question based on valid content.
    """
    kw = state.get("keyword")
    kw_data = state.get("keyword_data", {})
    
    # Use definitions to generate targeted Q
    questions = await generate_keyword_questions(
        keyword=kw,
        definition=kw_data.get("definition", ""),
        level="Intermediate" # Could comprise from user profile
    )
    
    if not questions:
         return {"messages": [AIMessage(content="Could not generate a quiz at this moment.")]}
         
    question = questions[0]
    return {
        "current_question": question,
        "messages": [AIMessage(content=f"**Q. {question['question_text']}**")]
    }

async def evaluate_answer_node(state: KeywordState):
    """
    [Evaluation Phase] Checks user answer.
    """
    current_q = state.get("current_question")
    if not current_q:
         return {"messages": [AIMessage(content="No active question to evaluate.")]}
         
    user_ans = state["messages"][-1].content
    
    eval_result = await evaluate_answer(
        question=current_q.get("question_text"),
        user_answer=user_ans,
        model_answer=current_q.get("model_answer"),
        evaluation_criteria=current_q.get("evaluation_criteria", [])
    )
    
    # Update Mastery in DB
    if state.get("user_db_id"):
        await keyword_service.update_user_mastery(
            user_id=state["user_db_id"], 
            keyword_key=current_q.get("primary_keyword", state.get("keyword")),
            result=eval_result
        )
    
    feedback = eval_result.get("feedback", "")
    score = eval_result.get("score", 0)
    passed = eval_result.get("is_passed", False)
    
    msg = f"**Assessment Result**: {'PASS ✅' if passed else 'TRY AGAIN ⚠️'} (Score: {score})\n\n{feedback}"
    
    return {
        "evaluation_result": eval_result,
        "messages": [AIMessage(content=msg)]
    }

async def recommend_node(state: KeywordState):
    """
    [Navigation Phase] Suggests next steps.
    """
    kw_data = state.get("keyword_data", {})
    related = kw_data.get("related_keywords", [])
    
    # If DB available, we could check user history to filter out learned topics
    
    # Call Navigator Agent
    result = await recommend_next_keywords(
        keyword=state.get("keyword", "None"),
        related_keywords=related
    )
    
    recs = result.get("recommendations", [])
    reason = result.get("reasoning", "")
    
    if recs:
        rec_text = f"**Next Keywords** (Reason: {reason})\n" + \
                   "\n".join([f"- {r}" for r in recs])
    else:
        rec_text = "What would you like to learn next?"
        
    return {
        "next_recommendations": recs,
        "messages": [AIMessage(content=rec_text)]
    }

# ==========================================
# 3. Edges & Graph
# ==========================================

def route_next(state: KeywordState):
    intent = state.get("user_intent")
    if intent == "KEYWORD_SEARCH":
        return "explain"
    elif intent == "ANSWER":
        return "evaluate"
    elif intent == "NAVIGATION":
        return "recommend"
    elif intent == "WAIT":
        return END
    return END # Chit chat or others

workflow = StateGraph(KeywordState)

# Nodes
workflow.add_node("router", router_node)
workflow.add_node("explain", search_and_explain_node)
workflow.add_node("quiz", generate_quiz_node)
workflow.add_node("evaluate", evaluate_answer_node)
workflow.add_node("recommend", recommend_node)

# Edges
workflow.add_edge(START, "router")

workflow.add_conditional_edges(
    "router",
    route_next,
    {
        "explain": "explain",
        "evaluate": "evaluate",
        "recommend": "recommend",
        END: END
    }
)

# Flow: Explain -> Quiz -> WAIT
workflow.add_edge("explain", "quiz")
workflow.add_edge("quiz", END) # Wait for answer

# Flow: Evaluate -> Recommend -> WAIT
workflow.add_edge("evaluate", "recommend")
workflow.add_edge("recommend", END)

keyword_graph = workflow.compile()
