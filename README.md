# 개발자의 성장이 현실이 되는 곳, TechTree
### 👉 [서비스 바로가기 : https://techtree.haebo.pro](https://techtree.haebo.pro) 👈

<img src="frontend/public/logo/techtree-logo.png" width="200" height="200" alt="TechTree Tree" style="border-radius: 50%; object-fit: cover;">

<br/>

> **TechTree**는 이력서와 채용 공고를 기반으로 실전 같은 **AI 실시간 음성 면접**을 경험하고, 성장을 위한 정교한 피드백을 받는 서비스입니다. 

> * **🎙️ AI 실시간 음성 면접**: OpenAI Realtime API(WebRTC)를 활용한 지연 없는 실시간 대화형 면접을 경험해보세요!
> * **📸 멀티모달 서류 분석**: 이력서(PDF)는 물론 채용 공고(이미지/텍스트)를 AI가 즉시 분석하여 맞춤형 질문을 생성합니다!
> * **📊 정밀 평가 및 리포트**: 면접 종료 후 성적표, 강점/약점 분석, 답변 피드백이 담긴 종합 리포트를 이메일로 받아보세요!
>
> ---
>
> 💡 **실시간 통신(WebRTC)** 의 속도감과 **에이전틱한 작업 흐름**의 정교함을 동시에 확보하도록 설계되었습니다.<br/>
> 💡 반복적인 **실전 연습**과 AI의 객관적인 **피드백**을 통해 면접 역량을 극대화합니다. 

> [TechTree Service UI](docs/service_screens.md)
![Service Capture](frontend/public/service/techtree-home.png)

## 📖 Index
- [Current Service Flow](#-current-service-flow): 현재 서비스 흐름 <br/>
- [Tech Stack](#-tech-stack): 사용 기술 및 도구 <br/>
- [Architecture & Agent Workflow](#-architecture--agent-workflow): 시스템 구조 <br/>
- [Documentation](#-documentation): 기획 및 설계 문서 <br/>
- [Git & Deployment](#-git--deployment): 브랜치 전략 및 배포 <br/>
- [Version History](#-version-history): 버전별 변경 사항 <br/>
- [Getting Started](#-getting-started): 설치 및 실행 방법

---

## ⭐ Current Service Flow

> 현재 운영 버전(v2.0.0)의 기본 흐름은 **초대코드 인증 → 정보 입력 → Realtime 음성 면접 → 완료 화면 → 이메일 리포트**입니다.

1. 사용자는 초대코드 인증 후 지원 직무, 경력, 학력, 이메일, 이력서, 채용 공고 정보를 입력합니다.
2. 프론트엔드는 입력값을 브라우저 세션에 저장하고 `/interview`로 이동합니다.
3. FastAPI 백엔드는 LangGraph manager로 면접 컨텍스트를 준비하고 OpenAI Realtime WebRTC client secret을 발급합니다.
4. 브라우저는 OpenAI Realtime에 WebRTC로 직접 연결하고, 사용자는 Space 기반 Push-to-Talk 방식으로 답변합니다.
5. 면접 종료 후 transcript와 실제 공고 데이터는 백엔드 평가 흐름에 전달됩니다.
6. LangGraph evaluator가 구조화된 평가 리포트를 생성하고, Resend를 통해 입력한 이메일로 발송합니다.

핵심 리포트 항목:

- 종합 점수
- 강점 및 개선점
- 주요 Q&A 피드백
- 말투/답변 습관 피드백
- 이력서 기반 자기소개 개선안
- 이력서-직무 적합도
- 전체 대화 내역

---

## ⭐ Tech Stack

> 프로젝트에 사용된 핵심 기술 및 인프라 구성입니다.

| Category | Technology | Description |
| --- | --- | --- |
| **Frontend** | ![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white) ![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black) ![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white) | Modern Web Application (App Router) |
| **Backend** | ![Python](https://img.shields.io/badge/python-3670A0?style=flat-square&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) | High-Performance API & Realtime Session Server |
| **AI / LLM** | ![OpenAI](https://img.shields.io/badge/OpenAI_Realtime-412991?style=flat-square&logo=openai&logoColor=white) ![LangGraph](https://img.shields.io/badge/LangGraph-FF4B4B?style=flat-square) ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white) | Realtime WebRTC & Agent Orchestration |
| **ExternalAPI** | ![WebRTC](https://img.shields.io/badge/WebRTC-333333?style=flat-square&logo=webrtc&logoColor=white) ![Tavily](https://img.shields.io/badge/Tavily-4285F4?style=flat-square) ![Resend](https://img.shields.io/badge/Resend-000000?style=flat-square) | Realtime Communication & External Services |
| **Cloud/DB** | ![AWS](https://img.shields.io/badge/AWS-232F3E?style=flat-square&logo=amazon-aws&logoColor=white) ![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white) | Cloud Infrastructure & Database |

--- 
## ⭐ Architecture & Agent Workflow
- **Frontend**: `Next.js (App Router)` 기반의 반응형 웹 서비스로 구현되었습니다.
- **Backend**: `FastAPI` 서버를 통해 OpenAI Realtime 세션 관리 및 비즈니스 로직을 처리합니다.
- **AI Engine**: `LangGraph`를 사용하여 면접 전 컨텍스트 준비, 면접 평가, 자기 비판(Self-Reflection) 기반 프롬프트 개선을 관리합니다.
- **Realtime**: `WebRTC` 기술을 활용하여 저지연 실시간 음성 통신을 지원합니다.

> [**System Architecture**](docs/architecture.md)
![TechTree v2.0 system architecture](docs/images/Techtree-Arch-v2.0.drawio.svg)
*(v2.0 아키텍처 다이어그램)*

> [**Agent Workflow**](docs/agent_workflow.md)
![TechTree v2.0 LangGraph workflow](docs/images/v2.0_agent_logic.png)
*(v2.0 랭그래프 워크플로우)*

---

## ⭐ Documentation

> 프로젝트의 모든 기획 및 설계 문서는 [`docs`](docs/README.md) 디렉토리 내에서 코드와 함께 관리됩니다.

### 📂 Documentation Structure

| Category | Description | Key Documents |
| --- | --- | --- |
| **서비스 (Product)** | 실제 화면과 사용자 흐름 | • [서비스 화면](docs/service_screens.md)<br>• [서비스 흐름도](docs/user_flow.md) |
| **기획 (PRD)** | 서비스 목표 및 개발 계획 | • [MVP 및 개발 계획](docs/mvp_and_plan.md)<br>• [TechTree Wiki](docs/techtree-wiki.md) |
| **설계 (Design)** | 시스템 및 AI 에이전트 설계 | • [시스템 아키텍처](docs/architecture.md)<br>• [AI 에이전트 워크플로우](docs/agent_workflow.md) |
| **지식 (Knowledge)** | 기술 의사결정 및 참고 자료 | • [기술 스택 선정 이유](docs/tech_decisions.md)<br>• [참고 레퍼런스](docs/references.md) |

---

## ⭐ Git & Deployment

> 본 프로젝트는 **개발(Dev)** 과 **운영(Prod)** 환경을 철저히 분리하여 데이터 안정성과 배포 속도를 모두 확보했습니다.

| Branch | Action & Role | Frontend | Backend | Database |
| :--- | :--- | :--- | :--- | :--- |
| **`develop`** | **Develop & Test**<br/>개발 및 로컬/도커 테스트 | **Localhost / Preview**<br/>(Dev Environment) | **Local Uvicorn / Docker Smoke Test** | **MongoDB Atlas**<br/>(Reflection/Policy, Invite) + **Local JSONL Fallback** |
| **`main` / `Tag`** | **Production**<br/>AWS 서버 배포 | **AWS EC2 Docker**<br/>(Next.js + Nginx) | **AWS EC2 Docker**<br/>(FastAPI/Uvicorn) | **MongoDB Atlas**<br/>(Reflection/Policy, Invite) + **AWS JSONL Fallback** |

---

## ⭐ Version History

> 현재 운영 버전은 **v2.0.0 Realtime Voice Interview**입니다.<br/>
> 아래는 프로젝트의 주요 릴리즈 및 변경 사항 내역입니다.<br/>

| Version | Feature | KeyTechnology | Release Date |
| :--- | :--- | :--- | :--- |
| [**v1.0.0**](https://github.com/haebo9/ai-techtree-project/tree/v1.0.0) | **MCP Tool Calling Agent**<br>MCP tool을 활용한 챗봇 서비스 | Langchain, MCP, FastAPI, AWS | 2026.01.15 |
| [**v1.1.0**](https://github.com/haebo9/ai-techtree-project/tree/v1.1.0) | **Agentic Quiz System**<br>키워드 기반 동적 문제 풀이 서비스 | LangGraph, MongoDB, Streamlit | 2026.03.02 |
| [**v1.1.1(lab)**](https://github.com/haebo9/ai-techtree-project/tree/v1.1.1(lab)) | **Multi-Agent Workflow**<br>LangGraph 기반 에이전트 워크플로우 고도화 | LangGraph, Sub-Agents, Next.js | - |
| [**v2.0.0**](https://github.com/haebo9/ai-techtree-project/tree/v2.0.0) | **Realtime Voice Interview**<br>실시간 음성 면접 및 멀티모달 분석 서비스 | OpenAI Realtime, WebRTC, Next.js | 2026.05.18 |

---

## ⭐ Getting Started
> 자세한 구축 과정은 [GUIDE.md](GUIDE.md) 문서를 참고하세요.

### Prerequisites (v2.0 Deployment)
- **Environment**:
   - **Python**: `3.12.13` (Release Version: python:3.12-slim)
   - **Node.js**: `22.x` (Release Version: node:22-slim)
   - **Next.js**: `16.2.6`
   - **React**: `19.2.6`

- **API Keys**(.env):
   - OPENAI_API_KEY (Required)
   - TAVILY_API_KEY (Job Search)
   - RESEND_API_KEY (Email Report)
   - MONGODB_URL (Optional reflection memory)

### Local Development

Backend:

```bash
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Useful URLs:

- Frontend: `http://localhost:3000`
- Debug page: `http://localhost:3000/debug`
- Backend docs: `http://localhost:8000/docs`

### Verification

```bash
.venv/bin/python -m compileall backend/app
```

```bash
cd frontend
npm run lint
npm run build
```
