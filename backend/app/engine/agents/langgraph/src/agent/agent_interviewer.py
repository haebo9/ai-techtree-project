from typing import List, Optional, Dict, Any
import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load AI_TECH_TREE from JSON
# Attempt to find tracks.json relative to this file
# This path assumes: backend/app/engine/agents/langgraph_tutorial/src/agent/interviewer_agent.py
TRACK_DB_PATH = os.path.join(os.path.dirname(__file__), "../../../../../source/tracks.json")

def _load_track_data():
    try:
        # Check if file exists at the calculated relative path
        if not os.path.exists(TRACK_DB_PATH):
            # Fallback check for standard structure if run from different context
            alt_path = "/Users/seo/Documents/develop/ai-techtree-project/backend/app/source/tracks.json"
            if os.path.exists(alt_path):
                with open(alt_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                print(f"Warning: tracks.json not found at {TRACK_DB_PATH} or {alt_path}")
                return {}
        
        with open(TRACK_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading track data: {e}")
        return {}

AI_TECH_TREE = _load_track_data()

# 1. 모델 초기화
api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(
    model="gpt-4o",  # Writer 역할이므로 좀 더 똑똑한 모델 사용 권장
    temperature=0.7, # 창의적인 멘트 생성을 위해 약간 높임
    api_key=api_key
)

# ---------------------------------------------------------------------
# Tools for Curriculum Navigation (Optional, if needed for Topic Selection)
# ---------------------------------------------------------------------

def get_curriculum_context(track: Optional[str] = None, tier: Optional[str] = None) -> str:
    """
    Retrieves specific curriculum data from the AI Tech Tree.
    Useful for understanding the context of the interview topic.
    """
    if not track:
        summary = {k: v.get("description", "") for k, v in AI_TECH_TREE.items()}
        return f"[Available Tracks]\n{json.dumps(summary, ensure_ascii=False, indent=2)}"

    track_data = AI_TECH_TREE.get(track)
    if not track_data:
        return "Selected Track information not found."

    if not tier:
        tiers_summary = list(track_data.get("tiers", {}).keys())
        return f"[Selected Track: {track}]\nAvailable Tiers: {json.dumps(tiers_summary, ensure_ascii=False, indent=2)}"
    
    tier_data = track_data.get("tiers", {}).get(tier)
    if not tier_data:
        return f"Selected Tier '{tier}' not found in {track}."
    
    return f"[Current Focus: {tier}]\nContents: {list(tier_data.keys())}"

# ---------------------------------------------------------------------
# Functional Chains (LangChain LCEL)
# ---------------------------------------------------------------------

# 1. Feedback Generation Chain
FEEDBACK_SYSTEM_PROMPT = """
당신은 AI TechTree의 친절하고 전문적인 면접관입니다.
지원자(사용자)의 답변에 대한 평가 결과를 바탕으로, 지원자에게 전달할 자연스러운 피드백 멘트를 작성하세요.

[입력 정보]
- 현재 질문: {question}
- 사용자 답변: {user_answer}
- 평가 점수: {score}점
- 통과 여부: {is_pass}
- 평가 상세(Feedback): {feedback}

[작성 가이드]
1. 말투: 정중하고 부드러운 '해요체'를 사용하세요. (예: "~~하셨군요!", "아, 이 부분은 ~~입니다.")
2. 내용: 
    - 점수가 높으면(70점 이상) 칭찬과 함께 답변의 핵심을 재확인해주세요.
    - 점수가 낮으면(70점 미만) 틀린 부분을 부드럽게 지적하고 격려해주세요.
3. 꼬리 질문(Deep Dive):
    - 만약 '통과 여부'가 False이거나, 답변이 완벽하지 않다면 핵심을 찌르는 꼬리 질문을 **하나만** 덧붙여주세요.
    - 이미 완벽하다면 꼬리 질문 없이 다음 문제로 넘어가자고 하세요.

[출력 예시]
"아, Dropout에 대해 잘 설명해주셨네요! 
하지만 데이터가 매우 적을 때 Dropout만으로 충분할까요? 이때 사용할 수 있는 다른 기법에 대해서도 말씀해 주시겠어요?"
"""

feedback_prompt = ChatPromptTemplate.from_messages([
    ("system", FEEDBACK_SYSTEM_PROMPT),
    ("human", "위 평가 내용을 바탕으로 면접관 멘트를 작성해주세요.")
])

feedback_chain = feedback_prompt | llm | StrOutputParser()


async def generate_feedback_message(question: str, user_answer: str, score: int, is_pass: bool, feedback: str) -> str:
    """
    평가 결과를 바탕으로 사용자에게 보낼 피드백 메시지(꼬리질문 포함)를 생성합니다.
    """
    return await feedback_chain.ainvoke({
        "question": question,
        "user_answer": user_answer,
        "score": score,
        "is_pass": is_pass,
        "feedback": feedback
    })


# 2. Report Formatting Chain (Optional)
REPORT_SYSTEM_PROMPT = """
당신은 AI TechTree의 면접 결과 리포트 작성자입니다.
Evaluator가 분석한 데이터를 바탕으로, 지원자가 읽기 편한 Markdown 형식의 종합 리포트를 작성하세요.
격식 있고 깔끔한 톤을 유지하세요.
"""

report_prompt = ChatPromptTemplate.from_messages([
    ("system", REPORT_SYSTEM_PROMPT),
    ("human", "[분석 데이터]\n{analysis_data}\n\n위 데이터를 예쁘게 포맷팅해주세요.")
])

report_chain = report_prompt | llm | StrOutputParser()

# 3. Topic Recommendation Chain
RECOMMEND_SYSTEM_PROMPT = """
당신은 AI TechTree의 면접 가이드입니다.
사용자의 관심사나 요청을 듣고, 제공된 [커리큘럼 목록] 중에서 가장 적합한 Track이나 Tier를 추천해주세요.

[커리큘럼 목록]
{context}

[가이드]
1. 사용자가 구체적인 주제를 언급하지 않았다면, 전체 Track을 간략히 소개하고 선택을 유도하세요.
2. 사용자가 특정 관심사(예: "백엔드", "AI")를 보였다면, 관련 Track과 그 안의 Tier들을 구체적으로 제안하세요.
3. 말투는 친절하고 전문적인 '해요체'를 사용하세요.
4. 이미 주제가 명확하다면 "그럼 [주제]로 면접을 시작할까요?" 라고 확인해주세요.
"""

recommend_prompt = ChatPromptTemplate.from_messages([
    ("system", RECOMMEND_SYSTEM_PROMPT),
    ("human", "{user_input}")
])

recommend_chain = recommend_prompt | llm | StrOutputParser()

async def recommend_topic_response(user_input: str) -> str:
    """
    사용자의 초기 입력에 대응하여 커리큘럼을 소개하거나 주제를 추천하는 멘트를 생성합니다.
    """
    # 1. 커리큘럼 정보 로드 (우선 전체 목록 조회)
    # TODO: 사용자 입력에서 키워드를 추출하여 특정 Track만 조회하는 로직으로 고도화 가능
    context_str = get_curriculum_context(track=None)
    
    # 2. 추천 멘트 생성
    response = await recommend_chain.ainvoke({
        "context": context_str,
        "user_input": user_input
    })
    
    return response


async def format_final_report(analysis_data: str) -> str:
    return await report_chain.ainvoke({"analysis_data": analysis_data})
