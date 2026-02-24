from fastapi import APIRouter
from app.api.endpoints import stateless_chat, stateful_chat, techtree

api_router = APIRouter()

# Unified Chat Endpoints
api_router.include_router(stateless_chat.router, prefix="/stateless", tags=["chat"])
api_router.include_router(stateful_chat.router, prefix="/stateful", tags=["chat"])
api_router.include_router(techtree.router, prefix="/techtree", tags=["techtree"])
