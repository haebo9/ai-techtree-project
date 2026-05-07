from langchain_core.messages import AIMessage, SystemMessage
from app.core.llm import get_llm
from app.engine.graphs.state import KeywordState
from app.engine.prompts.chat_prompt import SUPERVISOR_CHAT_SYSTEM_PROMPT, QUIZ_CHAT_SYSTEM_PROMPT

# ==========================================
# supervisor_chat_node -> SUPERVISOR
# ==========================================
# 일반적인 대화를 위한 노드 
async def supervisor_chat_node(state: KeywordState):
    """
    [supervisor_chat Phase] Handles general conversation and AI capability introduction.
    """
    agent_llm = get_llm(temperature=0.5)
    messages = state.get("messages", [])
    
    sys_prompt = SUPERVISOR_CHAT_SYSTEM_PROMPT
    
    # 기존 대화 내역 전체를 주입하되, 시스템 프롬프트로 튜터 역할과 안내 사항을 강제합니다.
    agent_msgs = [SystemMessage(content=sys_prompt)] + messages[-2:]
    print(agent_msgs)
    ai_response = await agent_llm.ainvoke(agent_msgs)
    
    return {"messages": [ai_response], "user_intent": "FINISH"}


# ==========================================
# quiz_chat_node -> QUIZ
# ==========================================
async def quiz_chat_node(state: KeywordState):
    """
    [Quiz Phase] Handles hint requests and general Q&A during a quiz.
    """
    from langchain_core.messages import SystemMessage
    from app.engine.nodes.tools import quiz_tools
    
    # 힌트를 이미 사용했는지 체크
    if state.get("hint_used", False):
        msg = AIMessage(content="🚫 이미 이 문제에 대한 힌트를 제공해 드렸습니다. 정답을 시도해 보세요!")
        return {"messages": [msg], "user_intent": "FINISH"}
    
    agent_llm = get_llm(temperature=0.4).bind_tools(quiz_tools)
    keyword = state.get("keyword", "알 수 없음")
    current_question = state.get("current_question")
    q_text = current_question.get("question_text") if current_question else "출제된 문제 없음"
    messages = state.get("messages", [])
    
    chat_sys_prompt = QUIZ_CHAT_SYSTEM_PROMPT.format(keyword=keyword, q_text=q_text)
    agent_msgs = [SystemMessage(content=chat_sys_prompt)] + messages
    ai_response = await agent_llm.ainvoke(agent_msgs)
    
    return {"messages": [ai_response], "user_intent": "FINISH", "hint_used": True}
