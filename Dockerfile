# Base Image
FROM python:3.13-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치 (필요시 git 등 추가)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# 의존성 패키지 설치
# 1. Backend Requirements
COPY backend/requirements.txt ./requirements-backend.txt
RUN pip install --no-cache-dir -r requirements-backend.txt

# 2. Frontend Requirements (혹시 모를 추가 의존성을 위해 분리 설치)
# (Deleted frontend/v1 dependencies for v1.1)

# 전체 프로젝트 코드 복사 (frontend, backend, docs 등 모두 포함)
COPY . .

# PYTHONPATH 설정
# 이렇게 하면 frontend/main.py 에서도 "from backend.app..." 처럼 접근 가능합니다.
ENV PYTHONPATH=/app/backend

# 포트 노출 (문서화 용도)
# 8000: Backend (FastAPI)
# 8100: Frontend (Streamlit)
# 8200: MCP Server (Tools)
EXPOSE 8000 8100 8200
