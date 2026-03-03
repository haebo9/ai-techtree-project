from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Import API Routers
from app.api.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        "message": "Welcome to AI TechTree", 
        "docs": {
            "mcp": "/mcp/docs",
            "api": "/docs"
        }
    }
