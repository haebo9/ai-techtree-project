from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

# LangGraph 워크플로우 불러오기
from app.engine.graphs.workflow import agent_workflow

router = APIRouter()

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
                stream_mode="updates"
            ):
                # 데이터 전송 (ensure_ascii=False로 한글 깨짐 방지 잘하셨습니다)
                yield f"data: {json.dumps(update, ensure_ascii=False)}\n\n"
        
        except Exception as e:
            logger.error(f"Stream Error: {str(e)}")
            yield f"data: {json.dumps({'error': '에이전트 실행 중 오류가 발생했습니다.'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")