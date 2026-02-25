from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.core.llm import get_llm
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from app.api_mcp.tools import MCP_TOOLS

router = APIRouter()

# -------------------------------------------------------------------------
# Pydantic Models (Request/Response)
# -------------------------------------------------------------------------
from app.schemas_api.chat import StatelessChatRequest, StatelessChatResponse

# -------------------------------------------------------------------------
# Agent Logic
# -------------------------------------------------------------------------
@router.post("/chat", response_model=StatelessChatResponse)
async def chat_endpoint(request: StatelessChatRequest):
    try:
        # 1. Initialize LLM with Tools
        llm = get_llm(temperature=0.2)
        tools = MCP_TOOLS
        llm_with_tools = llm.bind_tools(tools)

        # 2. Reconstruct LangChain Message History
        # 프론트엔드에서 받은 JSON 데이터를 LangChain 객체로 변환
        langchain_messages = []
        for msg in request.messages:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.role == "tool":
                # ToolMessage는 tool_call_id가 필수입니다.
                langchain_messages.append(ToolMessage(
                    content=msg.content,
                    tool_call_id=msg.id, 
                    name=msg.name
                ))
            # SystemMessage 등 필요시 추가

        # 3. Invoke Agent (Single Turn)
        # 이미 Tool 실행 결과가 포함된 히스토리라면, LLM은 다음 말을 하거나 멈춥니다.
        # 마지막 메시지가 User라면 LLM은 답변하거나 Tool을 호출합니다.
        
        # 주의: 여기서는 "한 턴"만 실행하고 결과를 프론트엔드에 돌려줍니다.
        # 프론트엔드가 Tool Call 응답을 받으면, Tool을 실행하고 다시 API를 호출해야 하는 구조가 *아니라*,
        # **백엔드에서 Tool 실행까지 다 끝내고 최종 답변만 줄지**, 
        # 아니면 **Tool 실행 요청을 프론트엔드에 줄지** 결정해야 합니다.
        
        # >> 사용자의 요구사항(Streamlit UI에서 Tool 실행 과정 보여주기)을 고려하면,
        # 백엔드 내부에서 Loop를 돌면서 Tool을 실행하고, 
        # "최종 답변"과 "중간에 실행했던 Tool 로그"를 함께 반환하는 것이 가장 깔끔합니다.

        tool_logs = []
        final_content = ""
        
        # Agent Loop
        current_messages = langchain_messages
        
        # 무한 루프 방지
        max_steps = 5
        step_count = 0

        while step_count < max_steps:
            step_count += 1
            
            # LLM 호출
            ai_msg = llm_with_tools.invoke(current_messages)
            
            # 1) Tool Call이 있는 경우
            if ai_msg.tool_calls:
                current_messages.append(ai_msg) # 대화 기록에 추가
                
                for tool_call in ai_msg.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]
                    
                    # Tool 실행
                    # tools 리스트 안의 요소가 LangChain Tool 객체일 수도 있고, 함수일 수도 있음
                    selected_tool = None
                    for t in tools:
                        # 1. LangChain Tool 객체인 경우 (.name 속성)
                        if hasattr(t, "name") and t.name == tool_name:
                            selected_tool = t
                            break
                        # 2. 파이썬 함수인 경우 (.__name__ 속성)
                        elif hasattr(t, "__name__") and t.__name__ == tool_name:
                            selected_tool = t
                            break
                    
                    tool_result_content = ""
                    
                    if selected_tool:
                        try:
                            # 실제 실행
                            # 함수라면 바로 호출(tool_args), Tool 객체라면 .invoke(tool_args)
                            if hasattr(selected_tool, "invoke"):
                                tool_result = selected_tool.invoke(tool_args)
                            else:
                                tool_result = selected_tool(**tool_args)
                                
                            tool_result_content = str(tool_result)
                        except Exception as e:
                            tool_result_content = f"Error: {str(e)}"
                    else:
                        tool_result_content = "Error: Tool not found."

                    # 로그 기록 (프론트엔드 전달용)
                    tool_logs.append({
                        "name": tool_name,
                        "args": tool_args,
                        "result": tool_result_content
                    })

                    # 대화 기록에 Tool 결과 추가 (그래야 LLM이 결과를 보고 이어감)
                    current_messages.append(ToolMessage(
                        tool_call_id=tool_id,
                        name=tool_name,
                        content=tool_result_content
                    ))
                
                # Loop 다시 실행 (Tool 결과 보고 LLM이 다시 생각)
                continue
            
            # 2) Tool Call 없이 답변만 있는 경우 (Loop 종료)
            else:
                final_content = ai_msg.content
                break
        
        return StatelessChatResponse(
            response=final_content,
            tool_calls=tool_logs
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
