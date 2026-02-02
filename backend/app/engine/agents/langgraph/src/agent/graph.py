from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Literal, TypedDict
from typing_extensions import Annotated
import os
from dotenv import load_dotenv, find_dotenv

# .env 파일 로드 (환경 변수 설정)
load_dotenv(find_dotenv('.env'))

from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# 로컬 에이전트 모듈 임포트
from agent.qamaker_agent import generate_questions
from agent.evaluator_agent import evaluate_answer, analyze_interview_result
from agent.interviewer_agent import generate_feedback_message, format_final_report, recommend_topic_response
from agent.router_agent import route_user_input

# 실제 백엔드 서비스 연동
# 주의: 실행 시 backend 경로가 PYTHONPATH에 포함되어야 함
from app.services.interview_service import interview_service


# ==========================================
# 1. 상태(State) 정의
# ==========================================
class InterviewState(TypedDict, total=False):
    """
    LangGraph에서 관리하는 인터뷰 세션의 전체 상태입니다.
    """
    # 대화 기록 (LangChain Message 객체 리스트, append 방식)
    messages: Annotated[List[BaseMessage], add_messages]
    
    # 사용자 및 학습 세션 정보
    user_id: str          # 세션 상의 사용자 ID
    user_db_id: str       # 실제 DB의 ObjectId (문자열)
    track: str            # 현재 진행 중인 트랙 (예: Python, AI)
    topic: str            # 세부 주제 (예: Generator, overfitting)
    level: str            # 난이도 (Basic, Intermediate, Advanced)
    
    # 내부 로직 상태
    generated_questions: List[dict]   # 미리 생성된 질문 큐 (Cache)
    current_question: Optional[dict]  # 현재 사용자에게 던져진 질문 정보
    evaluation_result: Optional[dict] # 가장 최근 답변에 대한 평가 결과
    star_gained: bool                 # 방금 질문에서 별(점수)을 획득했는지 여부
    user_intent: Optional[str]        # 라우터가 파악한 사용자 의도 (ANSWER, NEXT...)
    
    # 진행도 제어
    question_count: int   # 현재까지 진행한 질문 수
    max_questions: int    # 최대 질문 수 (세션 종료 기준)
    interview_complete: bool # 인터뷰 종료 플래그


# ==========================================
# 2. 노드(Node) 함수 정의
# ==========================================

async def load_state_node(state: InterviewState):
    """
    [초기화] 사용자 정보를 DB에서 조회하거나 생성하여 상태에 로드합니다.
    """
    params = {}
    
    # 기본값 설정
    uid = state.get("user_id", "guest")
    if not state.get("user_id"):
        params["user_id"] = uid
        
    # 사용자 DB 조회 (이메일 기반 가상 조회)
    if not state.get("user_db_id"):
        email = f"{uid}@techtree.com"
        nickname = f"User_{uid}"
        
        # 실제 DB 서비스 호출
        user = await interview_service.get_or_create_user(email, nickname)
        params["user_db_id"] = str(user.id)
    
    # 인터뷰 설정 기본값
    if not state.get("max_questions"):
        params["max_questions"] = 5
        
    return params

async def router_node(state: InterviewState):
    """
    [라우터] 사용자의 최신 입력을 분석하여 다음 의도(Intent)를 결정합니다.
    """
    messages = state["messages"]
    if not messages:
        return {"user_intent": "CONSULT"}
        
    last_msg = messages[-1]
    
    # AI가 마지막으로 말했으면 사용자 응답 대기 (WAIT)
    if isinstance(last_msg, AIMessage):
        return {"user_intent": "WAIT"}

    user_input = last_msg.content
    curr_topic = state.get("topic", "General")
    last_q_text = state.get("current_question", {}).get("question_text", "")
    
    # LLM Router 호출
    route_result = await route_user_input(user_input, curr_topic, last_q_text)
    intent = route_result.get("intent", "CONSULT")
    new_topic = route_result.get("topic")
    
    updates = {"user_intent": intent}
    
    # 주제 변경 요청 시 관련 상태 초기화
    if intent == "CHANGE_TOPIC" and new_topic:
        updates["topic"] = new_topic
        updates["generated_questions"] = [] # 기존 질문 큐 비우기
        
    return updates

async def consult_node(state: InterviewState):
    """
    [상담] 면접 질문 외의 일반 대화나 주제 추천을 처리합니다.
    """
    last_message = state["messages"][-1]
    user_input = last_message.content
    
    response_text = await recommend_topic_response(user_input)
    
    return {
        "messages": [AIMessage(content=response_text)]
    }

async def generate_question_node(state: InterviewState):
    """
    [질문 생성] 현재 트랙/주제에 맞는 기술 면접 질문을 생성합니다.
    """
    track = state.get("track", "Common")
    topic = state.get("topic", "General")
    level = state.get("level", "Intermediate")
    
    # 1. 캐시된 질문 확인
    questions = state.get("generated_questions", [])
    
    # 2. 없으면 새로 생성 (LLM 호출)
    if not questions:
        new_questions = await generate_questions(skill=track, topic=topic, level=level, count=1)
        if not new_questions:
             return {
                "messages": [AIMessage(content=f"죄송합니다. '{topic}' 주제에 대한 질문을 생성하는데 일시적인 문제가 발생했습니다.")],
             }
        questions = new_questions
        
    # 3. 질문 하나 꺼내기
    next_q = questions.pop(0)
    current_q_text = next_q.get("question_text", "")
    
    return {
        "generated_questions": questions, # 남은 질문 업데이트
        "current_question": next_q,       # 현재 활성 질문 설정
        "star_gained": False,             # 별 획득 플래그 초기화
        "messages": [AIMessage(content=current_q_text)]
    }

async def evaluate_answer_node(state: InterviewState):
    """
    [평가] 사용자의 답변을 채점하고 DB에 결과를 반영합니다.
    """
    current_q = state.get("current_question")
    if not current_q:
        return {"messages": [AIMessage(content="평가할 질문이 없습니다. 넘어갑니다.")]}
        
    last_message = state["messages"][-1]
    user_answer = last_message.content
        
    # 1. AI 평가 수행
    eval_result = await evaluate_answer(
        question=current_q.get("question_text", ""),
        user_answer=user_answer,
        model_answer=current_q.get("model_answer", "N/A"),
        evaluation_criteria=current_q.get("evaluation_criteria", [])
    )
    
    # 2. DB 업데이트 (별 부여 로직)
    star_gained = False
    if state.get("user_db_id"):
        subject = current_q.get("topic", state.get("topic", "General"))
        is_passed = eval_result.get("is_passed", False)
        score = eval_result.get("score", 0)
        
        # 실제 DB 서비스 호출
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
    [피드백] 평가 결과에 따라 피드백 메시지(꼬리 질문 포함)를 생성합니다.
    """
    eval_result = state.get("evaluation_result", {})
    current_q = state.get("current_question", {})
    star_gained = state.get("star_gained", False)
    
    # 피드백 문구 생성
    feedback_msg = await generate_feedback_message(
        question=current_q.get("question_text", ""),
        user_answer=state["messages"][-1].content,
        score=eval_result.get("score", 0),
        is_pass=eval_result.get("is_passed", False),
        feedback=eval_result.get("feedback", "")
    )
    
    final_output = feedback_msg
    # 별 획득 시 축하 메시지 추가
    if star_gained:
        final_output = f"🎉 **[별 획득!]** 축하합니다! 해당 주제({current_q.get('topic', 'General')})의 숙련도가 상승했습니다. ⭐\n\n" + final_output
    
    return {
        "messages": [AIMessage(content=final_output)]
    }

async def final_report_node(state: InterviewState):
    """
    [리포트] 인터뷰 세선 종료 후 종합 리포트를 제공합니다.
    """
    history = [f"{m.type}: {m.content}" for m in state["messages"]]
    analysis_data = await analyze_interview_result(history)
    analysis_str = str(analysis_data) 
    final_report = await format_final_report(analysis_str)
    
    return {
        "messages": [AIMessage(content=final_report)],
        "interview_complete": True
    }


# ==========================================
# 3. 조건부 엣지(Edge) 로직
# ==========================================

def check_router_intent(state: InterviewState) -> Literal["generate", "evaluate", "consult", "report", "end"]:
    """라우터 결과에 따라 다음 노드를 결정합니다."""
    intent = state.get("user_intent")
    
    if intent == "ANSWER":
        # 질문이 활성화된 상태여야 평가 가능
        if state.get("current_question"):
            return "evaluate"
        else:
            return "generate" # 질문이 없으면 새로 생성
            
    elif intent in ["NEXT_QUESTION", "CHANGE_TOPIC"]:
        return "generate"
        
    elif intent == "CONSULT":
        return "consult"
        
    elif intent == "QUIT":
        return "report"
        
    return "consult" # 기본값

def check_continue_interview(state: InterviewState) -> Literal["generate", "report"]:
    """피드백 후 인터뷰를 계속할지 종료할지 결정합니다."""
    count = state.get("question_count", 0)
    max_q = state.get("max_questions", 10) 
    
    # 최대 질문 수 도달 시 종료
    if count >= max_q:
        return "report"
    
    # 연속 진행 (Momentum 유지)
    return "generate"


# ==========================================
# 4. 그래프 구성 (Workflow Construction)
# ==========================================

workflow = StateGraph(InterviewState)

# (1) 노드 등록
workflow.add_node("load_state", load_state_node)
workflow.add_node("router", router_node)
workflow.add_node("consult", consult_node)
workflow.add_node("generate_question", generate_question_node)
workflow.add_node("evaluate_answer", evaluate_answer_node)
workflow.add_node("provide_feedback", feedback_node)
workflow.add_node("final_report", final_report_node)

# (2) 엣지 연결
# 시작 -> 상태 로드 -> 라우터
workflow.add_edge(START, "load_state")
workflow.add_edge("load_state", "router")

# 라우터 분기
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

# 평가 -> 피드백 순차 연결
workflow.add_edge("evaluate_answer", "provide_feedback")

# 피드백 이후 (계속 진행 vs 종료)
workflow.add_conditional_edges(
    "provide_feedback",
    check_continue_interview,
    {
        "generate": "generate_question",
        "report": "final_report"
    }
)

# 끝 지점 설정 (Turn 종료 후 대기)
workflow.add_edge("generate_question", END) # 질문 던지고 사용자 입력 대기
workflow.add_edge("consult", END)           # 상담 답변 후 대기
workflow.add_edge("final_report", END)      # 리포트 후 종료

# (3) 컴파일
graph = workflow.compile()
