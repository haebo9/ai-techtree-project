########################################
# API Router
########################################
# /api/로 시작하는 모든 요청을 처리할 router
from fastapi import APIRouter

api_router = APIRouter()

######################################### 
# Unified Chat Endpoints
######################################### 
# /api/chat 요청을 처리할 router
from app.api import chat

api_router.include_router(chat.router, prefix='/chat', tags=['chat'])