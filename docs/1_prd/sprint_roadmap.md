# 📅 Project Roadmap: AI TechTree & MCP Nexus
> **Timeline**: 2025.12.01 ~ 2026.05.31 (Total 6 Months)  
> **Strategy**: **MCP First & Web Next** - MCP 개발을 통해 Core Logic(백엔드+AI)을 우선 완성하고, 이후 웹 프론트엔드를 결합하여 완성도를 높인다.

## 📝 Phase 0: Planning & Design 
`2025.12 초 ~ 2025.12 중순`
> **Goal**: 서비스의 방향성 정의 및 핵심 문서화 완료

- [x] **Sprint 0 (12월 1주~3주): 기획 및 기술 조사**
    - [x] 서비스 컨셉 구체화 (AI TechTree, Skill Sync)
    - [x] 핵심 기능 정의 (User Flow, PRD 작성)
    - [x] 기술 스택 선정 및 아키텍처 설계 (Tech Decisions)
    - [x] Agent 구현 계획 및 개념 정의
    - [x] MCP 서버 설계 문서 작성

---

## 🏗 Phase 1: Core Logic & MCP Server (Contest Prep)
`2025.12 말 ~ 2026.01 말`
> **Goal**: **Kakao MCP Player 10 출품 (1/18)** 및 **v1.1 Multi-Agent System** 구현을 목표로 한다. <br/>
> *이 단계에서 개발된 백엔드 로직은 추후 웹 서비스(v2)의 핵심 엔진으로 확장된다.*

- [x] **Sprint 1 (12월 3주~4주): 환경 구축 및 기본 로직**
    - [x] **AWS**: AI Agent 기본 구조 구현 및 테스트
    - [x] **DB**: MongoDB Atlas 클러스터 생성 및 스키마 설계 (`questions`, `sessions`)
    - [x] **DB**: DB collection 구조 설계 및 스키마 저장 로직 구현
    - [x] **Dummy Data**: DB에 기본 데이터 추가(Agent 로직 테스트)
    - [x] **Backend**: FastAPI 프로젝트 Scaffolding 및 환경 변수 설정
    - [x] **AI Core**: LangChain 기반의 단순 질의응답(Interviewer) 로직 구현 (CLI 테스트)
    
- [x] **Sprint 2 (1월 1주): AI 에이전트 고도화**
    - [x] **Evaluator**: 답변 체점 및 피드백 생성 로직 구현 (Beta)
    - [x] **QAmaker**: 문제 생성 에이전트 구현 (Beta)
    - [x] **Interviewer**: 면접관 에이전트 구현 (Beta)

- [x] **Sprint 3 (1월 2주): MCP Server & AWS Deploy**
    - [x] **MCP Wrapping**: 완성된 AI 로직을 `get_techtree_*` 툴로 포장 (mcp-server)
    - [x] **Deployment**: Docker 빌드 및 AWS EC2 배포
    - [x] **Stateless HTTP**: Kakao MCP Player 호환을 위한 Stateless HTTP Endpoint 설정

- [x] **Sprint 4 (1월 3주): MCP Polish & Submission** (`~01.18`)
    - [x] **Refinement**: Tool Output 구조화 (JSON) 및 복합 툴 호출 로직 개선
    - [x] **Documentation**: `mcp_server.md` 문서 현행화 및 사용 가이드 작성
    - [x] **🚀 MCP player 10 출품 완료** 
    - [x] **🚀 Web Service v1.0.0 Launch**

- [ ] **Sprint 5 (1월 4주): v1.1 Multi-Agent Core (Streamlit)**
    - [ ] **LangGraph**: 단일 체인을 Stateful한 그래프 구조로 마이그레이션 (Context 관리)
    - [ ] **Agents**: 면접관(Interviewer), 평가자(Evaluator) 에이전트 고도화
    - [ ] **Chatbot UI**: Streamlit 기반의 임시 채팅 인터페이스 구현 (Logic 검증용)
    - [ ] **Logic Verification**: 꼬리물기, 평가, 피드백 사이클 완결성 검증
    - [ ] **🚀 v1.1.0 Release** (Agent Impl Verified)

---

## ⚡ Phase 2: Web Service & Agent Completion (MVP)
`2026.02 초 ~ 2026.02 말`
> **Goal**: 웹 프론트엔드 구축(Vercel) -> 서비스 연동의 **순차적 프로세스**를 통해 MVP(v2.0.0)를 완성한다.

- [ ] **Sprint 6 (2월 1주): Frontend Foundation & UI Implementation**
    - [x] **Setup**: Next.js 16 + TypeScript + Custom Design System 환경 구축
    - [x] **Deploy**: Vercel 배포 파이프라인 연결 및 도메인 연동
    - [ ] **UI Implementation**: 랜딩 페이지, TechTree 시각화(ReactFlow Mockup), 채팅 인터페이스(UI Only) 구현
    - [ ] **Navigation**: 주요 페이지 라우팅 (/login, /dashboard, /interview)

- [ ] **Sprint 7 (2월 2주): Backend API & Persistence**
    - [ ] **API V2**: 프론트엔드와 통신할 Stateful Chat API (Streaming 지원) 개발
    - [ ] **DB Persistence**: 면접 기록, 평가 결과, 유저 상태를 MongoDB에 저장하는 로직
    - [ ] **Optimization**: Agent 응답 속도 및 RAG 검색 효율 최적화

- [ ] **Sprint 8 (2월 3주~4주): Integration & MVP Launch Prep**
    - [ ] **Integration**: Frontend(Next.js) <-> Backend(FastAPI) API 연동
    - [ ] **Real-time Chat**: AI 답변 스트리밍 처리를 위한 Hook 및 이벤트 핸들링 구현
    - [ ] **Auth**: 사용자 세션 및 인증 처리
    - [ ] **Polish**: E2E 테스트 및 UI 디자인 디테일 수정
    - [ ] **🚀 Web Service v2.0.0 Launch**

---

## 🔧 Phase 3: Iteration & Scale-up
`2026.03 ~ 2026.04`
> **Goal**: 사용자 피드백을 반영하여 성능을 개선하고 기능을 확장한다.

- [ ] **Sprint 9 (3월 1주~2주): Performance Tuning**
    - [ ] **Caching**: Redis 도입으로 중복 질문 생성 방지 및 속도 개선
    - [ ] **Optimization**: DB 인덱싱 최적화 및 에이전트 응답 속도 단축

- [ ] **Sprint 10 (3월 3주~4주): Advanced Features**
    - [ ] **My Data**: 사용자별 학습 리포트 및 성장 기록 대시보드
    - [ ] **Community**: 트랙 마스터 명예의 전당 등 소셜 기능 맛보기

## 💎 Phase 4: Stabilization & Maintenance
`2026.05 ~`
> **Goal**: 코드 품질 향상 및 장기 운영 체제 수립

- [ ] **Sprint 11 (5월): Refactoring & Documentation**
    - [ ] **Test Coverage**: Pytest/Jest 커버리지 80% 이상 확보
    - [ ] **Blog**: 기술 블로그 작성 (MCP 도입기, LangGraph 시행착오 등)
