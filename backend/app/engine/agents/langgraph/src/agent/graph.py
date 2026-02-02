from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal, TypedDict
from typing_extensions import Annotated
import os
from dotenv import load_dotenv, find_dotenv

# Automatically find and load the .env file from the project root or parents
load_dotenv(find_dotenv('.env'))

from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# Import local agents (ported from legacy)
from agent.qamaker_agent import generate_questions
from agent.evaluator_agent import evaluate_answer, analyze_interview_result
from agent.interviewer_agent import generate_feedback_message, format_final_report, recommend_topic_response
from agent.router_agent import route_user_input

# Import real backend services
# Note: Ensure that the 'backend' directory is in PYTHONPATH for 'app' imports to work.
from app.services.interview_service import interview_service


# 1. State Definition
class InterviewState(TypedDict, total=False):
    # Standard LangChain/LangGraph message history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Session Context
    user_id: str
    user_db_id: str
    track: str
    topic: str
    level: str
    
    # Internal State
    generated_questions: List[dict]  # Queue of questions
    current_question: Optional[dict] # Currently active question (that the user is answering)
    evaluation_result: Optional[dict] # Result of the last evaluation
    star_gained: bool # Flag to check if star was gained in parsing turn
    user_intent: Optional[str] # Router decision: ANSWER, NEXT_QUESTION, CHANGE_TOPIC, CONSULT, QUIT
    
    # Progress
    question_count: int
    max_questions: int
    interview_complete: bool


# 2. Nodes

async def load_state_node(state: InterviewState):
    """
    [Init] Ensure User Exists and Load State
    """
    # Initialize defaults if not present
    params = {}
    if not state.get("user_id"):
        params["user_id"] = "guest"
        
    if not state.get("user_db_id"):
        # For prototype, use a fixed guest email or derive from user_id if possible
        uid = state.get("user_id", "guest")
        email = f"{uid}@techtree.com"
        nickname = f"User_{uid}"
        
        user = await interview_service.get_or_create_user(email, nickname)
        params["user_db_id"] = str(user.id)
    
    # Set default config if missing
    if not state.get("max_questions"):
        params["max_questions"] = 5
        
    return params

async def router_node(state: InterviewState):
    """
    [Router] Analyze User Intent and Route
    """
    messages = state["messages"]
    if not messages:
        # Should not happen if initiated correctly, but default to CONSULT
        return {"user_intent": "CONSULT"}
        
    last_msg = messages[-1]
    
    # If the last message is AI, we are waiting for User.
    if isinstance(last_msg, AIMessage):
        return {"user_intent": "WAIT"}

    user_input = last_msg.content
    curr_topic = state.get("topic", "General")
    last_q_text = state.get("current_question", {}).get("question_text", "")
    
    # Use Router Agent
    route_result = await route_user_input(user_input, curr_topic, last_q_text)
    intent = route_result.get("intent", "CONSULT")
    new_topic = route_result.get("topic")
    
    updates = {"user_intent": intent}
    
    if intent == "CHANGE_TOPIC" and new_topic:
        updates["topic"] = new_topic
        updates["generated_questions"] = [] # Clear cache on topic switch
        
    return updates

async def consult_node(state: InterviewState):
    """
    [Phase 1] Consultation / General Chat
    """
    last_message = state["messages"][-1]
    user_input = last_message.content
    
    response_text = await recommend_topic_response(user_input)
    
    return {
        "messages": [AIMessage(content=response_text)]
    }

async def generate_question_node(state: InterviewState):
    """
    [Phase 2] Generate Question
    """
    # Initialize defaults if missing
    track = state.get("track", "Common")
    topic = state.get("topic", "General")
    level = state.get("level", "Intermediate")
    
    # Check Cache (generated_questions queue)
    questions = state.get("generated_questions", [])
    
    if not questions:
        # Cache Miss -> Generate New
        # v1.2 Plan: Use RAG / Offline Worker. v1.1: Live Generation
        new_questions = await generate_questions(skill=track, topic=topic, level=level, count=1)
        
        if not new_questions:
             return {
                "messages": [AIMessage(content=f"죄송합니다. '{topic}' 주제에 대한 질문을 생성하는데 일시적인 문제가 발생했습니다.")],
             }
             
        questions = new_questions
        
    # Deliver Question
    if not questions:
        return {"messages": [AIMessage(content="질문 목록이 비어있습니다.")]}
        
    next_q = questions.pop(0)
    current_q_text = next_q.get("question_text", "")
    
    return {
        "generated_questions": questions,
        "current_question": next_q,
        "star_gained": False, # Reset star flag for new question
        "messages": [AIMessage(content=current_q_text)]
    }

async def evaluate_answer_node(state: InterviewState):
    """
    [Phase 2] Evaluate and Update DB
    """
    current_q = state.get("current_question")
    if not current_q:
        return {"messages": [AIMessage(content="평가할 질문이 없습니다. 넘어갑니다.")]}
        
    last_message = state["messages"][-1]
    user_answer = last_message.content
        
    # 1. AI Evaluation
    eval_result = await evaluate_answer(
        question=current_q.get("question_text", ""),
        user_answer=user_answer,
        model_answer=current_q.get("model_answer", "N/A"),
        evaluation_criteria=current_q.get("evaluation_criteria", [])
    )
    
    # 2. DB Update (Skill & Stars)
    star_gained = False
    if state.get("user_db_id"):
        subject = current_q.get("topic", state.get("topic", "General"))
        is_passed = eval_result.get("is_passed", False)
        score = eval_result.get("score", 0)
        
        star_gained = await interview_service.update_skill_status(
            user_id=state["user_db_id"], 
            subject=subject, 
            passed=is_passed, 
            score=score
        )
    
    return {
        "evaluation_result": eval_result,
        "question_count": state.get("question_count", 0) + 1,
        "star_gained": star_gained
    }

async def feedback_node(state: InterviewState):
    """
    [Phase 2] Feedback
    """
    eval_result = state.get("evaluation_result", {})
    current_q = state.get("current_question", {})
    star_gained = state.get("star_gained", False)
    
    feedback_msg = await generate_feedback_message(
        question=current_q.get("question_text", ""),
        user_answer=state["messages"][-1].content,
        score=eval_result.get("score", 0),
        is_pass=eval_result.get("is_passed", False),
        feedback=eval_result.get("feedback", "")
    )
    
    final_output = feedback_msg
    if star_gained:
        final_output = f"🎉 **[별 획득!]** 축하합니다! 해당 주제({current_q.get('topic', 'General')})의 숙련도가 상승했습니다. ⭐\n\n" + final_output
    
    return {
        "messages": [AIMessage(content=final_output)]
    }

async def final_report_node(state: InterviewState):
    """
    [Phase 3] Final Report
    """
    history = [f"{m.type}: {m.content}" for m in state["messages"]]
    analysis_data = await analyze_interview_result(history)
    analysis_str = str(analysis_data) 
    final_report = await format_final_report(analysis_str)
    
    return {
        "messages": [AIMessage(content=final_report)],
        "interview_complete": True
    }


# 3. Conditional Logic

def check_router_intent(state: InterviewState) -> Literal["generate", "evaluate", "consult", "report", "end"]:
    intent = state.get("user_intent")
    
    if intent == "ANSWER":
        # Check if we actually have a question to answer
        if state.get("current_question"):
            return "evaluate"
        else:
            return "generate" # Treat as next/start if no question active
            
    elif intent in ["NEXT_QUESTION", "CHANGE_TOPIC"]:
        return "generate"
        
    elif intent == "CONSULT":
        return "consult"
        
    elif intent == "QUIT":
        return "report"
        
    return "consult" # Default

def check_continue_interview(state: InterviewState) -> Literal["generate", "report"]:
    count = state.get("question_count", 0)
    max_q = state.get("max_questions", 10) 
    
    if count >= max_q:
        return "report"
    
    return "generate"


# 4. Graph Construction

workflow = StateGraph(InterviewState)

# Add Nodes
workflow.add_node("load_state", load_state_node)
workflow.add_node("router", router_node)
workflow.add_node("consult", consult_node)
workflow.add_node("generate_question", generate_question_node)
workflow.add_node("evaluate_answer", evaluate_answer_node)
workflow.add_node("provide_feedback", feedback_node)
workflow.add_node("final_report", final_report_node)

# Entry Point
workflow.add_edge(START, "load_state")
workflow.add_edge("load_state", "router")

# Router Edges
workflow.add_conditional_edges(
    "router",
    check_router_intent,
    {
        "evaluate": "evaluate_answer",
        "generate": "generate_question",
        "consult": "consult",
        "report": "final_report",
        "end": END
    }
)

# Interview Loop
workflow.add_edge("evaluate_answer", "provide_feedback")

# After feedback, usually we want to give the NEXT question immediately in this flow's design?
# "GenQ -> Deliver -> Wait -> Eval -> Reward -> Feedback -> PROBABLY_WAIT_OR_NEXT"
# If we simply END after feedback, the user has to say "Next".
# Include Logic: If answer was Good, auto-next? Or just end.
# v1.1 Design says "Router -- Continue --> CheckDB ...".
# Let's simple chain to GenerateQuestion to keep momentum (Continuous Interview).
workflow.add_conditional_edges(
    "provide_feedback",
    check_continue_interview,
    {
        "generate": "generate_question",
        "report": "final_report"
    }
)

# After generating question, we stop and wait for user.
workflow.add_edge("generate_question", END)

# After Consult, we stop
workflow.add_edge("consult", END)

# After Report, we stop
workflow.add_edge("final_report", END)

# Compile
graph = workflow.compile()
