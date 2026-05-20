from fastapi import APIRouter
from app.api import interview, invite, upload

api_router = APIRouter()

api_router.include_router(invite.router, prefix="/invite", tags=["Invite"])

# 면접 관련 엔드포인트를 라우터에 포함합니다.
api_router.include_router(interview.router, prefix="/interview", tags=["Interview"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
