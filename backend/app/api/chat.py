from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
from datetime import datetime
from langchain_core.messages import BaseMessage

# LangGraph 워크플로우 불러오기
from app.engine.graphs.graph import agent_workflow

# logger 불러오기 
from app.core.logger import get_logger
logger = get_logger(__name__)

# router 생성
router = APIRouter()

######################################################
# Function
######################################################
# JSON 직렬화가 안 되는 객체(datetime 등)를 처리하는 함수 정의
def json_serializable(obj):
    # 1. datetime 처리 (기존 로직)
    if isinstance(obj, datetime):
        return obj.isoformat()
    
    # 2. LangChain 메시지 객체 처리 (추가)
    # AIMessage, HumanMessage 등이 BaseMessage를 상속받습니다.
    if isinstance(obj, BaseMessage):
        return {
            "type": obj.type,
            "content": obj.content,
            "metadata": getattr(obj, "response_metadata", {})
        }
    
    # 3. Pydantic 모델 처리 (LangGraph의 일부 객체 대응)
    if hasattr(obj, "dict") and callable(obj.dict):
        return obj.dict()

    raise TypeError(f"Type {type(obj)} not serializable")

######################################################
# Router
######################################################
# [POST] /api/chat/stream -> 실시간 에이전트 답변
@router.post("/stream")
async def stream_interview(data: dict):
    user_message = data.get("message")
    thread_id = data.get("thread_id", "default_session") # 세션 유지를 위한 ID

    if not user_message:
        raise HTTPException(status_code=400, detail="메시지가 비어있습니다.")

    async def event_generator():
        try:
            # config에 thread_id를 넣어줘야 이전 대화를 기억함
            config = {"configurable": {"thread_id": thread_id}}
            
            async for update in agent_workflow.astream(
                {"messages": [("user", user_message)]}, 
                config=config,
                stream_mode="updates" # updates(리턴한 값만), values(상태 바뀔때 마다), logs(디버그용)
            ):
                # 데이터 전송 (ensure_ascii=False로 한글 깨짐 방지 잘하셨습니다)
                yield f"data: {json.dumps(update, ensure_ascii=False, default=json_serializable)}\n\n"
        
        except Exception as e:
            logger.error(f"Stream Error: {str(e)}")
            yield f"data: {json.dumps({'error': '에이전트 실행 중 오류가 발생했습니다.'}, ensure_ascii=False, default=json_serializable)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")