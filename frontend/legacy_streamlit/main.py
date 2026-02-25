import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# -------------------------------------------------------------------------
# Environment & Configuration
# -------------------------------------------------------------------------
# Load .env
current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, "../.env"))

# Backend URL Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_ENDPOINT = f"{BACKEND_URL}/api/v1/agent/chat"

st.set_page_config(page_title="AI TechTree MCP", page_icon="", layout="wide")

st.title("😃 AI TechTree MCP")
st.caption(f"Backend Connected: {BACKEND_URL}")

# -------------------------------------------------------------------------
# Session State for Chat History
# -------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        AIMessage(content="안녕하세요! AI 커리큘럼 추천, 로드맵 조회, 최신 트렌드 검색을 도와드릴 수 있습니다. 무엇을 도와드릴까요?"), 
    ]

# -------------------------------------------------------------------------
# UI: Display Chat History
# -------------------------------------------------------------------------
for msg in st.session_state["messages"]:
    if isinstance(msg, HumanMessage):
        st.chat_message("user").write(msg.content)
    elif isinstance(msg, AIMessage):
        st.chat_message("assistant").write(msg.content)
    elif isinstance(msg, ToolMessage):
        # ToolMessage는 Expander로 깔끔하게 표시
        with st.expander(f"🛠️ Tool Output: {msg.name}"):
            st.code(msg.content, language="json")

# -------------------------------------------------------------------------
# Chat Logic: Handle User Input
# -------------------------------------------------------------------------
if prompt := st.chat_input("예: 데이터 분석 학습 순서 알려줘"):
    # 1. User Message Display & Save
    st.chat_message("user").write(prompt)
    st.session_state["messages"].append(HumanMessage(content=prompt))

    # 2. Call Backend API
    with st.chat_message("assistant"):
        with st.spinner("AI is Thinking..."):
            try:
                # Prepare Payload
                # 객체 -> JSON 변환 (role, content 만 추출)
                # ToolMessage는 API 요청에 포함하지 않아도 됨 (필요시 포함 가능하지만, 현재 로직상 불필요)
                filtered_history = []
                for m in st.session_state["messages"]:
                    if isinstance(m, HumanMessage):
                        filtered_history.append({"role": "user", "content": m.content})
                    elif isinstance(m, AIMessage):
                        filtered_history.append({"role": "assistant", "content": m.content})
                
                payload = {"messages": filtered_history}
                
                # API 호출
                response = requests.post(API_ENDPOINT, json=payload)
                response.raise_for_status()
                
                data = response.json()
                ai_response = data.get("response", "")
                tool_calls = data.get("tool_calls", [])

                # 3. Display Tool Logs (복원된 스타일)
                for tool in tool_calls:
                    tool_name = tool["name"]
                    tool_result = tool["result"]
                    tool_args = tool.get("args", {})
                    
                    # Toast 알림 (이전 스타일 복원)
                    st.toast(f"🛠️ {tool_name} 도구를 실행했습니다.", icon="🔧")
                    
                    # UI 표시 (Expander)
                    with st.expander(f"⚡ Tool Execution: {tool_name}"):
                        st.json(tool_args)
                        st.code(tool_result, language="json") # 결과가 JSON 문자열일 확률이 높음
                    
                    # 히스토리에 ToolMessage로 저장 (그래야 UI 루프에서 다시 그려짐)
                    st.session_state["messages"].append(ToolMessage(
                        tool_call_id=f"tool_{tool_name}", # 임시 ID
                        name=tool_name,
                        content=str(tool_result)
                    ))

                # 4. Display Final Answer
                if ai_response:
                    st.write(ai_response)
                    st.session_state["messages"].append(AIMessage(content=ai_response))

            except requests.exceptions.ConnectionError:
                st.error(f"❌ 백엔드 서버({BACKEND_URL})에 연결할 수 없습니다.")
            except Exception as e:
                st.error(f"❌ 오류가 발생했습니다: {str(e)}")
