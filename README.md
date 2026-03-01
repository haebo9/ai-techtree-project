# AI TechTree
> **<h3>"개발자의 성장이 게임이 되는 곳, AI TechTree"</h3>**

<img src="backend/app/source/techtree-tree.png" width="300" height="300" alt="TechTree Tree" style="border-radius: 50%; object-fit: cover;">

<br/>


> **AI TechTree**는 **AI 면접관**과 실시간으로 대화하며 기술 역량을 증명하고, RPG 게임처럼 **스킬 트리**를 채워나가는 서비스입니다.
> 단순한 문제 풀이가 아닌, **꼬리에 꼬리를 무는 심층 인터뷰** 를 통해 당신의 '진짜 실력'을 진단합니다.
>
> * **🕵️ AI 심층 면접**: 답변에 따라 달라지는 동적 질문 생성
> * **🌳 라이브 스킬 트리**: 내 강점과 약점을 한눈에 보여주는 시각화
> * **⚔️ 커리어 RPG**: '전직' 시스템으로 즐기는 성장
>
> ---
>
> 💡 **Engineering Philosophy**
> 본 프로젝트는 **LangGraph 기반의 Multi-Agent 시스템**과 **MCP 프로토콜**을 활용하여 **"AI 주도형 아키텍처 (AI-Driven Architecture)"** 를 완성했습니다.
> 1인 개발자로서 **기획(PRD)부터 배포(CI/CD)** 까지의 **Full-Cycle Engineering**을 통해, **AI 로직의 깊이(Deep-Dive)** 와 **인프라의 효율성(Lean)** 을 균형 있게 달성했습니다.

## 📖 Index
- [Documentation](#documentation): 기획 및 설계 문서 <br/>
- [Tech Stack](#tech-stack): 사용 기술 및 도구 <br/>
- [Architecture](#architecture): 시스템 구조 <br/>
- [Git & Deployment](#git--deployment): 브랜치 전략 및 배포 <br/>
- [Version History](#version-history): 버전별 변경 사항 <br/>
- [Roadmap](#roadmap): 개발 일정 <br/>
- [Getting Started](#getting-started): 설치 및 실행 방법

---

## ⭐ Documentation

> 프로젝트의 모든 기획 및 설계 문서는 `docs` 디렉토리 내에서 코드와 함께 관리됩니다.

### 📂 Documentation Structure

| Directory | Description | Key Documents |
| --- | --- | --- |
| [**1_prd**](docs/1_prd) | **기획 (Product Spec)**<br>요구사항 및 서비스 흐름 정의 | • [핵심 기능 명세](docs/1_prd/product_spec.md)<br>• [페르소나 정의](docs/1_prd/personas.md)<br>• [서비스 흐름도](docs/1_prd/user_flow.md)<br>• [스프린트 로드맵](docs/1_prd/sprint_roadmap.md) |
| [**2_design**](docs/2_design) | **설계 (System Design)**<br>시스템 아키텍처 및 기술 설계 | • [시스템 아키텍처](docs/2_design/architecture.md)<br>• [AI 에이전트 설계](docs/2_design/agent_workflow.md)<br>• [DB 스키마](docs/2_design/db_schema.md)<br>• [MCP 서버 설계](docs/2_design/mcp_server.md)<br> |
| [**3_knowledge**](docs/3_knowledge) | **지식 (Knowledge Base)**<br>기술 의사결정 및 참고 자료 | • [기술 스택 선정](docs/3_knowledge/tech_decisions.md)<br>• [참고 자료](docs/3_knowledge/references.md) |

👉 [전체 문서 목록 보기](docs/README.md)<br/>
👉 [개발 로그 보기](dev_log.md)<br/>
👉 [파일 구조 보기](STRUCTURE.md)

---

## ⭐ Tech Stack

> 프로젝트에 사용된 핵심 기술 및 인프라 구성입니다.

| Category | Technology | Description |
| --- | --- | --- |
| **Frontend** | ![Next.js](https://img.shields.io/badge/Next.js-black?style=flat-square&logo=next.js&logoColor=white) ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white) ![React Flow](https://img.shields.io/badge/React%20Flow-FF0072?style=flat-square&logo=react&logoColor=white) | Interactive UI/UX & Visualization |
| **Backend** | ![Python](https://img.shields.io/badge/python-3670A0?style=flat-square&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)  | High-Performance API & Container |
| **AI / LLM** | ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white) ![LangGraph](https://img.shields.io/badge/LangGraph-FF4B4B?style=flat-square) ![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white) ![MCP](https://img.shields.io/badge/MCP-000000?style=flat-square) ![Tavily](https://img.shields.io/badge/Tavily-4285F4?style=flat-square) | AI Agents & Workflow Orchestration |
| **Cloud/DB** | ![AWS](https://img.shields.io/badge/AWS-232F3E?style=flat-square&logo=amazon-aws&logoColor=white) ![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white) ![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white) | Cloud Infrastructure & Database |

--- 
## ⭐ Architecture
- **Frontend**: `Next.js`로 구축되어 `Vercel`을 통해 배포됩니다.(자동배포)
- **Backend**: `FastAPI` 서버를 `Docker container`로 빌드하여 `AWS(EC2)`에서 실행합니다.
- **Database**: `MongoDB Atlas`를 사용하여 데이터 안정성을 확보합니다.
- **AI Engine**: `LangGraph` 기반의 Multi-Agent 시스템이 코드 분석 및 평가를 수행합니다.

![alt text](backend/app/source/langgraph_arch.png)
---
## ⭐ Git & Deployment

> 본 프로젝트는 **개발(Dev)** 과 **운영(Prod)** 환경을 철저히 분리하여 데이터 안정성과 배포 속도를 모두 확보했습니다.
> **Docker 기반의 일관된 환경**과 **Vercel/AWS의 클라우드 자원**을 효율적으로 결합하여 **Cost-Effective**한 인프라를 구축했습니다.

| Branch | Action & Role | Frontend | Backend | Database |
| :--- | :--- | :--- | :--- | :--- |
| **`develop`** | **Develop & Test**<br/>개발 및 로컬 테스트 | **Localhost / Preview**<br/>(Dev Environment) | **Local Docker**<br/>(Consistency Test) | **MongoDB Atlas**<br/>(Dev) |
| **`main` / `Tag`** | **Production**<br/>실제 라이브 서비스 | **Vercel Prod**<br/>(Edge Network + CDN) | **AWS EC2**<br/>(t3.small + Docker) | **MongoDB Atlas**<br/>(Prod) |

---

## ⭐ Version History

> 프로젝트의 주요 릴리즈 및 변경 사항 내역입니다.

| Version | Feature | KeyTechnology | Release Date |
| :--- | :--- | :--- | :--- |
| **v1.0.0** | **MCP Tool Calling Agent**<br>MCP tool을 활용한 챗봇 서비스 | Langchain, MCP, FastAPI, AWS, streamlit | 2026.01.15<br/>(서비스 중) |
| **v1.1.0** | **Agentic Quiz System**<br>키워드 기반 동적 문제 풀이 서비스 | LangGraph, MongoDB, Langsmith | 2026.02.28<br/> |
| **v1.2.0** | **Web Service & Agent**<br>웹 화면 통합 서비스 | Next.js, Vercel, RAG, MongoDB | 2026.03.15<br/> |
| **v2.0.0** | **AI TechTree Full Release**<br>정식 서비스 출시 | - | 2026.04.01<br/> |

## ⭐ Sprint Roadmap
> 상세한 개발 일정과 스프린트 계획은 [Sprint Roadmap](docs/1_prd/sprint_roadmap.md) 문서를 참고하세요.

| Phase | Focus & Sprints | Period |
| :--- | :--- | :--- |
| **Phase 0** | **Planning & Design**<br>(Sprint 0) 기획 및 기술 조사 | 2025.12 |
| **Phase 1** | **MCP & Multi-Agent (v1.1)**<br>(Sprint 1-5) AI Core Logic, MCP, LangGraph Agent | 2025.12 ~ 2026.02 |
| **Phase 2** | **Web Service MVP (v1.2)**<br>(Sprint 6-8) Next.js Frontend & Stateful Integration | 2026.03 |
| **Phase 3** | **Iteration & Scale-up (v2.0)**<br>(Sprint 9-10) 성능 개선 및 고도화 | 2026.03 ~ 04 |
| **Phase 4** | **Polish & Stabilization**<br>(Sprint 11) 안정성 확보 및 유지보수 | 2026.05 ~ |

---

## ⭐ Getting Started
> `docs/README.md`를 참고하여 개발 환경을 구축할 수 있습니다.

### Prerequisites
- **Environment**:
  - Docker & Docker Compose 
  - Node.js v22.12.0+
  - Python 3.13.11+
- **API Keys**:
  - OpenAI API Key
  - Tavily API Key
- **Infrastructure**:
  - MongoDB Atlas
  - AWS EC2 Instance

### 1. Environment Setup
프로젝트 루트 경로에 `.env` 파일을 생성합니다. 아래 키들은 필수로 포함되어야 합니다.

```bash
# .env Configuration

# Project Settings
PROJECT_NAME="AI TechTree"
API_V1_STR="/api/v1"
API_V2_STR="/api/v2"

# AI & Search Keys
OPENAI_API_KEY="sk-..."
TAVILY_API_KEY="tvly-..."

# Database
MONGODB_URL="mongodb+srv://..."
DB_NAME="ai_techtree_dev"
```

### 2. Run Local Server (Docker)
로컬 환경에서 전체 스택(Backend + Frontend + MCP + Nginx)을 실행하는 권장 방법입니다.

```bash
# 1. Build & Run (Force Rebuild)
docker-compose -f docker-compose.local.yml up -d --build

# 2. Check Logs
docker-compose -f docker-compose.local.yml logs -f

# 3. Stop Server
docker-compose -f docker-compose.local.yml down
```
> **Access Points:**
> - Frontend (Next.js v2): http://localhost:8100
> - Backend Docs: http://localhost:8000/docs
> - MCP Server: http://localhost:8200/mcp

### 3. Deploy to AWS
AWS EC2 프로덕션 환경에 배포하는 방법입니다.

> **1. For AWS (Local Mac)**: 이미지를 빌드하여 Hub에 푸시하고, 설정 파일을 전송합니다.
```bash
docker build --no-cache --platform linux/amd64 -t haebo/ai-techtree:v1 .
docker push haebo/ai-techtree:v1
scp -r nginx techtree-server:~/
scp docker-compose.yml .env techtree-server:~/
```

> **2. In AWS (Server)**: 서버에 접속하여 최신 이미지를 풀(Pull) 받고 실행합니다.
```bash
# Local terminal: 
ssh techtree-server
# AWS terminal:
docker-compose pull
docker-compose down
docker-compose up -d --remove-orphans
docker-compose logs -f
```
> **Access Points:**
> - Frontend: https://haebo.pro
> - MCP Server: https://haebo.pro/mcp

### 4. Database Setup
MongoDB에 필요한 인덱스를 생성하고 TechTree 데이터를 동기화하는 초기화 스크립트를 실행합니다.

```bash
# Run init scripts inside the backend container
docker-compose -f docker-compose.local.yml exec backend sh -c "python scripts/init_db.py && python scripts/sync_track_to_db.py"
```

### 5. LangSmith Server (Local Test)
To monitor and interact with the LangGraph agent locally using LangSmith (LangGraph Studio):

1. **Setup Agent Environment**
   Create a `.env` file in `backend/` (or copy from root) with the following:
   ```env
   OPENAI_API_KEY=sk-...
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_PROJECT=ai-techtree-agent
   LANGCHAIN_API_KEY=lsv2_...
   MONGODB_URL=mongodb://root:example@localhost:27017/ai_techtree?authSource=admin
   ```

2. **Run LangGraph Studio Server**
   Since the architecture is unified, simply run `langgraph dev` from the `backend/` root folder where `langgraph.json` resides.
   ```bash
   cd backend
   
   # Run Server (LangGraph CLI will automatically detect langgraph.json)
   langgraph dev
   ```

3. **Access Studio**
   Open [http://localhost:2024](http://localhost:2024) in your browser.

### 6. Run Streamlit App (Local Test)
To test the LangGraph agent interaction via a Streamlit dashboard locally:

1. **Setup Agent Environment**
   Ensure your `.env` file in the `backend/` directory is configured as shown in the previous step.

2. **Run Streamlit Server**
   ```bash
   cd backend
   streamlit run tests/streamlit_dashboard.py
   ```

3. **Access Dashboard**
   Open [http://localhost:8501](http://localhost:8501) in your browser.
