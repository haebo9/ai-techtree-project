import pytest
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# Import our tools
from app.mcp.tools import MCP_TOOLS

# Load environment variables
load_dotenv()

@pytest.fixture
def llm_with_tools():
    """
    Initializes OpenAI LLM and binds the MCP tools.
    This simulates the Kakao PlayMCP environment where the LLM has access to these tools.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not found in environment. Skipping integration tests.")
        
    # Using 'gpt-5-mini' to test tool selection capability
    llm = ChatOpenAI(model="gpt-4.1", temperature=0) 
    return llm.bind_tools(MCP_TOOLS)

def test_get_ai_track(llm_with_tools):
    """
    Scenario 1: User asks for career advice (Diagnosis).
    Expected: LLM calls 'get_ai_track'.
    """
    print("\n[Test] Diagnosis Tool Selection")
    query = "저는 웹 개발을 좀 해봤는데, 요즘엔 데이터랑 수학 쪽이 재밌더라고요. 어떤 쪽으로 공부하면 좋을까요? 초보자입니다."
    
    # Invoke LLM
    response = llm_with_tools.invoke([HumanMessage(content=query)])
    
    # Assertions
    assert response.tool_calls, "LLM should have decided to call a tool."
    tool_call = response.tool_calls[0]
    
    print(f" -> Selected Tool: {tool_call['name']}")
    print(f" -> Arguments: {tool_call['args']}")
    
    assert tool_call["name"] == "get_ai_track"
    assert "interests" in tool_call["args"]
    
    # Check if keywords were extracted reasonably (Support both English and Korean)
    args_str = str(tool_call["args"]["interests"]).lower()
    assert any(k in args_str for k in ["data", "데이터"]), "Should detect data interest"
    assert any(k in args_str for k in ["math", "수학"]), "Should detect math interest"

def test_get_ai_path(llm_with_tools):
    """
    Scenario 2: User asks for curriculum (Roadmap).
    Expected: LLM calls 'get_ai_path'.
    """
    print("\n[Test] Roadmap Tool Selection")
    query = "AI 모델러가 되고 싶은데 커리큘럼 좀 알려줘. 'Track 2: AI Modeler / Researcher' 트랙으로 보여줘."
    
    response = llm_with_tools.invoke([HumanMessage(content=query)])
    
    assert response.tool_calls
    tool_call = response.tool_calls[0]
    
    print(f" -> Selected Tool: {tool_call['name']}")
    print(f" -> Arguments: {tool_call['args']}")

    assert tool_call["name"] == "get_ai_path"
    assert "track_name" in tool_call["args"]
    assert "Track 2" in tool_call["args"]["track_name"]

def test_get_ai_trends(llm_with_tools):
    """
    Scenario 3: User asks for latest news (Trends).
    Expected: LLM calls 'get_ai_trends'.
    """
    print("\n[Test] Trend Tool Selection")
    query = "요즘 RAG랑 AI Agent 기술 트렌드가 어때? 최신 뉴스 좀 찾아줘."
    
    response = llm_with_tools.invoke([HumanMessage(content=query)])
    
    assert response.tool_calls
    tool_call = response.tool_calls[0]
    
    print(f" -> Selected Tool: {tool_call['name']}")
    print(f" -> Arguments: {tool_call['args']}")
    
    assert tool_call["name"] == "get_ai_trends"
    assert "keywords" in tool_call["args"]
    # Check for keywords related to the query
    args_str = str(tool_call["args"]["keywords"]).lower()
    assert any(k in args_str for k in ["rag", "agent"]), "Should detect RAG or Agent keywords"
