from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Import API Routers
from app.api.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/api/docs", # docs 경로 명시 
    openapi_url="/api/openapi.json" # 스웨거 요청 경로 명시
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "https://techtree.haebo.pro",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Include API Routers 
# '/api'로 시작하는 모든 요청은 api_router로 전달
app.include_router(api_router, prefix="/api")


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to TechTree", 
        "docs": {
            "mcp": "/mcp/docs",
            "api": "/api/docs"
        }
    }
