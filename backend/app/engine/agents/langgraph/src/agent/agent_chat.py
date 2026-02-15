from langchain_core.messages import AIMessage
from app.engine.agents.langgraph.src.agent.state import KeywordState

# ==========================================
# Nodes
# ==========================================
# 일반적인 대화를 위한 노드 
async def chit_chat_node(state: KeywordState):
    """
    [Chit-Chat Phase] Handles general conversation.
    """
    response = "도움이 필요하시면 언제든지 말씀해주세요."
    return {"messages": [AIMessage(content=response)]}
