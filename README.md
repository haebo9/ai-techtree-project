# 🏆 AI Developer Ranking Service

> **"AI 면접관과 함께 성장하는 RPG형 개발자 커리어 로드맵, AI TechTree"**
>
> 단순한 지식 점검을 넘어, **AI 에이전트와의 심층 인터뷰**를 통해 기술 숙련도를 진단하고 시각화해주는 서비스입니다.
> 사용자는 **전직 시스템(1~3차)**과 **보스 챌린지**를 통해 자신의 성장을 게임처럼 즐길 수 있습니다.
>
> *본 프로젝트는 기획(PRD)부터 디자인, 개발, 배포까지 1인 개발자로서 현업 수준의 프로세스를 엄격히 준수하며 진행됩니다.*

## 🔗 Project Documentation

> 이 프로젝트의 관련 상세 내용은 **Notion**에서 관리되고 있습니다. 

 [![Notion](https://img.shields.io/badge/Notion-Project%20Page-black?style=for-the-badge&logo=notion&logoColor=white)](https://www.notion.so/6b3b0428beb64fce97b07a5585430d77?t=2bdc4afac1bf80b8b1d300a9877e5988)

### 📂 What's inside Notion?
- **Discovery**: 서비스 컨셉, 페르소나(Persona), 유저 저니 맵
- **Design**: 시스템 아키텍처, DB 스키마, API 명세서
- **Dev Log**: 스프린트별 회고 및 기술적 트러블슈팅 기록

---

## 🛠 Tech Stack & Infrastructure

> 프로젝트에 사용된 핵심 기술 및 인프라 구성입니다.

| Category | Technology | Description |
| --- | --- | --- |
| **Frontend** | ![Next.js](https://img.shields.io/badge/Next.js-black?style=flat-square&logo=next.js&logoColor=white) ![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat-square&logo=vercel&logoColor=white) | UI/UX & Client Deployment |
| **Backend** | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white) ![AWS](https://img.shields.io/badge/AWS-232F3E?style=flat-square&logo=amazon-aws&logoColor=white) | Server API & Cloud Hosting |
| **AI / LLM** | ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white) ![LangGraph](https://img.shields.io/badge/LangGraph-FF4B4B?style=flat-square) ![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat-square&logo=openai&logoColor=white) | AI Agents & Workflow Orchestration |
| **Database** | ![MongoDB Atlas](https://img.shields.io/badge/MongoDB%20Atlas-47A248?style=flat-square&logo=mongodb&logoColor=white) | Cloud NoSQL Database |

## 🏗 System Architecture

- **Frontend**: Next.js로 구축되어 **Vercel**을 통해 배포됩니다.
- **Backend**: FastAPI 서버를 **Docker** 컨테이너로 빌드하여 **AWS (EC2)**에서 실행합니다.
- **Database**: **MongoDB Atlas (Cloud)**를 사용하여 데이터 안정성을 확보합니다.
- **AI Engine**: LangGraph 기반의 Multi-Agent 시스템이 코드 분석 및 평가를 수행합니다.

---

## 📅 Roadmap (2025.12 ~ 2026.04)

> *각 단계는 Agile 스프린트 단위로 진행됩니다.*

- [ ] **Phase 1: Discovery & Basics (12월)**
    - 기획(PRD), 페르소나 설정, Python 비동기/OOP 학습
- [ ] **Phase 2: AI Core Development (1월)**
    - LangGraph 에이전트 설계 및 구현 (코드 분석/평가 로직)
- [ ] **Phase 3: Backend & DB (2월)**
    - FastAPI 구축 및 MongoDB Atlas 연동
- [ ] **Phase 4: Frontend Implementation (3월)**
    - Next.js UI 구현 및 Vercel 배포 (CI/CD)
- [ ] **Phase 5: Dockerizing & AWS Deploy (4월)**
    - 백엔드 Docker 이미지 빌드 및 AWS 서버 배포, 최종 런칭

---

## 🏃 Getting Started

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

# Run Server
uvicorn main:app --reload
