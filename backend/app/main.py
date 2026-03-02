from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Import API Routers
from app.api.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Unified Backend for Web Client (REST) and PlayMCP (Agent)",
    version="1.1.0"
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
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "message": "Welcome to AI TechTree Nexus", 
        "docs": {
            "mcp": "/mcp/docs",
            "api_v1": "/docs"
        }
    }
