# AI TechTree

> **<h3>"개발자의 성장이 게임이 되는 곳, AI TechTree"</h3>**

> **AI TechTree**는 **AI 면접관**과 실시간으로 대화하며 기술 역량을 증명하고, RPG 게임처럼 **스킬 트리**를 채워나가는 서비스입니다.
> 단순한 문제 풀이가 아닌, **꼬리에 꼬리를 무는 심층 인터뷰(LangGraph)** 를 통해 당신의 '진짜 실력'을 진단합니다.
>
> * **🕵️ AI 심층 면접**: 답변에 따라 달라지는 동적 질문 생성
> * **🌳 라이브 스킬 트리**: 내 강점과 약점을 한눈에 보여주는 시각화
> * **⚔️ 커리어 RPG**: '전직' 시스템으로 즐기는 성장
>
> ---
>
> 💡 **Engineering Philosophy**
> 본 프로젝트는 **1인 개발자**로서 **기획(PRD)부터 배포(CI/CD)** 까지의 **전체 엔지니어링 사이클**을 현업 수준으로 수행했습니다.
> **"AI 코어의 고도화(Deep-Dive)"** 와 **"인프라의 효율성(Lean)"** 을 동시에 달성하기 위한 전략적 선택들을 문서화했습니다.

1.  [Documentation](#documentation)
2.  [Tech Stack](#tech-stack)
3.  [Architecture](#architecture)
4.  [Git & Deployment](#git--deployment)
5.  [Roadmap](#roadmap)
6.  [Getting Started](#getting-started)

---

## Documentation

> 프로젝트의 모든 기획 및 설계 문서는 `docs` 디렉토리 내에서 코드와 함께 관리됩니다.

### 📂 Documentation Structure

| Directory | Description | Key Documents |
| --- | --- | --- |
| [**1_prd**](docs/1_prd) | **기획 (Product Spec)**<br>요구사항 및 서비스 흐름 정의 | • [핵심 기능 명세](docs/1_prd/product_spec.md)<br>• [페르소나 정의](docs/1_prd/personas.md)<br>• [서비스 흐름도](docs/1_prd/user_flow.md) |
| [**2_design**](docs/2_design) | **설계 (System Design)**<br>시스템 아키텍처 및 기술 설계 | • [시스템 아키텍처](docs/2_design/architecture.md)<br>• [AI 에이전트 설계](docs/2_design/agent_workflow.md)<br>• [DB 스키마](docs/2_design/db_schema.md) |
| [**3_knowledge**](docs/3_knowledge) | **지식 (Knowledge Base)**<br>기술 의사결정 및 트러블슈팅 | • [기술 스택 선정](docs/3_knowledge/tech_decisions.md)<br>• [트러블슈팅 로그](docs/3_knowledge/troubleshooting) |

👉 [전체 문서 목록 보기](docs/README.md)

---

## Tech Stack

> 프로젝트에 사용된 핵심 기술 및 인프라 구성입니다.

| Category | Technology | Description |
| --- | --- | --- |
| **Frontend** | ![Next.js](https://img.shields.io/badge/Next.js-black?style=flat-square&logo=next.js&logoColor=white) ![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white) | UI/UX & Client Deployment |
| **Backend** | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white) ![AWS](https://img.shields.io/badge/AWS-232F3E?style=flat-square&logo=amazon-aws&logoColor=white) | Server API & Cloud Hosting |
| **AI / LLM** | ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white) ![LangGraph](https://img.shields.io/badge/LangGraph-FF4B4B?style=flat-square) ![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white) | AI Agents & Workflow Orchestration |
| **Database** | ![MongoDB Atlas](https://img.shields.io/badge/MongoDB%20Atlas-47A248?style=flat-square&logo=mongodb&logoColor=white) | Cloud NoSQL Database |

## Architecture

- **Frontend**: Next.js로 구축되어 **Vercel**을 통해 배포됩니다.
- **Backend**: FastAPI 서버를 **Docker** 컨테이너로 빌드하여 **AWS (EC2)** 에서 실행합니다.
- **Database**: **MongoDB Atlas (Cloud)** 를 사용하여 데이터 안정성을 확보합니다.
- **AI Engine**: LangGraph 기반의 Multi-Agent 시스템이 코드 분석 및 평가를 수행합니다.

---
## Git & Deployment

> 본 프로젝트는 1인 개발의 효율성과 서비스 안정성을 위해 **GitHub Flow**를 변형한 **3-Tier 전략**을 따릅니다.
> **로컬 중심의 개발**과 **Vercel/AWS의 무료 티어**를 적극 활용하여 비용 '0원'의 인프라를 구축했습니다.

| Branch | Action & Role | Frontend | Backend | Database |
| :--- | :--- | :--- | :--- | :--- |
| **`feature/*`** | **Develop**<br/>기능 단위 개발 | **Localhost :3000**<br/>(Hot Reloading) | **Localhost :8000**<br/>(Docker Compose) | **MongoDB Atlas<br/>**(Dev) |
| **`main`** | **Staging**<br/>PR 통합 및 테스트 | **Vercel Preview**<br/>(PR 시 자동 배포) | **Local Docker**<br/>(Prod simulation) | **MongoDB Atlas<br/>**(Dev) |
| **`production`** | **Release**<br/>실제 사용자 배포 | **Vercel Prod**<br/>(Edge Network + CDN) | **AWS EC2**<br/>(t3.small + Docker) | **MongoDB Atlas<br/>**(Prod) |

---

## Roadmap
> *각 단계는 Agile 스프린트 단위로 진행되며, 상황에 따라 유동적으로 변경될 수 있습니다.*
> **(2025.12 ~ 2026.04)**

### **Phase 1: Discovery & Basics (2025.12)**
- [x] **기획 및 설계 (Docs)**
    - [x] 서비스 기획 (PRD, User Flow, Persona)
    - [x] 시스템 아키텍처 및 DB 설계
    - [x] 기술 스택 선정 및 ADR 작성
- [x] **개발 환경 및 전략 수립 (Infra)**
    - [x] Monorepo 구조 셋업 (Frontend, Backend, Docs)
    - [x] Git Branch 전략 (Feature -> Main -> Prod) 및 문서화
- [ ] **프로젝트 초기화 (Scaffolding)**
    - [ ] **Backend**: FastAPI 프로젝트 생성 및 의존성 관리(Poetry/Pip)
    - [ ] **Frontend**: Next.js 15 + Shadcn/ui 설치 및 실행 확인
    - [ ] **Code Quality**: Lint/Formatter 설정 (Ruff, ESLint, Prettier)
    

### **Phase 2: AI Core Development (2026.01)**
- [ ] **AI 에이전트 프로토타이핑**
    - [ ] LangGraph 기반 State Graph 설계 (면접관/평가자)
    - [ ] OpenAI API 연동 및 Prompt Engineering 테스트
- [ ] **에이전트 기능 구현**
    - [ ] 1:1 인터뷰 진행 로직 (Interviewer Agent)
    - [ ] 실시간 답변 분석 및 꼬리 질문 생성
    - [ ] 최종 피드백 및 등급 평가 로직 (Evaluator Agent)

### **Phase 3: Backend & DB (2026.02)**
- [ ] **API 서버 구축 (FastAPI)**
    - [ ] FastAPI 기본 라우팅 및 Pydantic 모델 정의
    - [ ] SSE(Server-Sent Events) 기반 스트리밍 API 구현
- [ ] **데이터베이스 연동 (MongoDB)**
    - [ ] Atlas 클라우드 연동 및 CRUD 구현
    - [ ] Chat History 및 스킬 트리 데이터 저장 로직

### **Phase 4: Frontend Implementation (2026.03)**
- [ ] **UI/UX 구현 (Next.js)**
    - [ ] Shadcn/ui 기반 공통 컴포넌트 개발
    - [ ] 채팅 인터페이스 (Streaming 텍스트 렌더링)
    - [ ] ReactFlow 기반 스킬 트리 시각화 (Interactive Graph)
- [ ] **연동 및 최적화**
    - [ ] Backend API 연동 및 상태 관리 (Zustand/TanStack Query)

### **Phase 5: Dockerizing & AWS Deploy (2026.04)**
- [ ] **배포 및 운영 (DevOps)**
    - [ ] Backend Docker 이미지 빌드 및 최적화
    - [ ] AWS EC2 인스턴스 셋업 및 Docker Compose 배포
    - [ ] Vercel 프로덕션 배포 및 도메인 연결
    - [ ] 최종 E2E 테스트 및 서비스 런칭 (v1.0)

---

## Getting Started
> `docs/README.md`를 참고하여 개발 환경을 구축할 수 있습니다.

### Prerequisites
- Python 3.9.6
- Node.js v25.2.1
- Docker & Docker Compose
- OpenAI API Key

### Backend Setup
```bash
cd backend
# Create Virtual Environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Dependencies
pip install -r requirements.txt
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Run Server
```bash
uvicorn main:app --reload
```