# Technical Decisions & Stack Architecture

> **AI TechTree** 프로젝트의 기술 스택 의사결정 문서(ADR)입니다.
> **Python 백엔드 중심의 고도화**와 **나머지 영역의 효율적 구현(Lean)**을 핵심 원칙으로 삼아 선정했습니다.

1.  [Frontend Architecture](#1-frontend-architecture)
2.  [Backend Architecture](#2-backend-architecture)
3.  [AI & Intelligence Engine](#3-ai--intelligence-engine)
4.  [Infrastructure & Deployment](#4-infrastructure--deployment)
5.  [FAQ](#5-faq)

---

## 1. Frontend Architecture

>백엔드 로직 구현에 집중하기 위해, 프론트엔드는 **생산성**과 **시각화**에 초점을 맞춥니다.

| Technology | Selection Rationale | Pros & Cons |
| :--- | :--- | :--- |
| **Next.js** | **Standard**: Vercel 배포 편의성과 React 생태계 활용을 위한 업계 표준.<br/>**Routing**: 별도 설정 없는 파일 시스템 기반 라우팅 사용. | **(+)** 최적화 자동화, 압도적인 레퍼런스.<br/>**(-)** Python 개발자에게는 React 학습 곡선 존재. |
| **Shadcn/ui** | **Speed**: CSS를 바닥부터 짜지 않고, 완성된 컴포넌트를 복사하여 개발 시간 단축.<br/>**Lean**: 무거운 라이브러리 설치 없이 필요한 코드만 가져옴. | **(+)** 디자인 고민 불필요, 높은 자유도.<br/>**(-)** TailwindCSS 선수 지식 필요. |
| **ReactFlow** | **Visualization**: 핵심 기능인 '스킬 트리' 시각화를 직접 구현하는 것은 비효율적임.<br/>**Interactive**: 줌, 팬, 드래그 기능을 기본 제공하는 라이브러리 채택. | **(+)** 복잡한 그래프 UI를 즉시 구현 가능.<br/>**(-)** 커스텀 노드 구현 시 React 심화 지식 필요. |

---

## 2. Backend Architecture

>프로젝트의 핵심 엔진입니다. **Python 비동기 처리**를 통해 AI 모델 서빙과 실시간 통신을 고성능으로 처리합니다.

| Technology | Selection Rationale | Pros & Cons |
| :--- | :--- | :--- |
| **FastAPI** | **AI-Native**: LangChain, OpenAI 등 Python AI 생태계와의 완벽한 통합.<br/>**Async**: LLM의 긴 응답 대기 시간을 Non-blocking으로 처리하여 동시성 확보. | **(+)** Pydantic 기반의 빠른 데이터 검증, 자동 문서화.<br/>**(-)** Django 대비 기본 기능(Admin 등) 부재. |
| **SSE** | **Lean-Protocol**: AI 답변 스트리밍은 서버에서 클라이언트로의 단방향 통신임.<br/>**Simplicity**: 무거운 WebSocket 대신 HTTP 표준인 SSE를 사용하여 구현 복잡도 최소화. | **(+)** 구현이 매우 간단하며 방화벽 친화적.<br/>**(-)** 양방향 통신 불가(필요 시 REST API 병행). |

---

## 3. AI & Intelligence Engine

>단순 LLM 호출을 넘어, **상태(State)**를 관리하고 **판단**하는 에이전트 시스템을 구축합니다.

| Technology | Selection Rationale | Pros & Cons |
| :--- | :--- | :--- |
| **LangGraph** | **Stateful-Agent**: 인터뷰의 문맥을 유지하고, 질문과 답변의 루프를 제어하기 위한 표준 도구.<br/>**Control**: 자율 에이전트보다 개발자가 흐름을 명확히 통제 가능. | **(+)** 복잡한 순환형 워크플로우 구현 최적화.<br/>**(-)** LangChain 대비 높은 러닝 커브. |
| **OpenAI** | **Reliability**: JSON 응답을 강제하는 Structured-Output 기능이 가장 안정적임.<br/>**Reasoning**: 평가 및 피드백 생성 시 높은 논리력 필요. | **(+)** 개발 편의성, 압도적인 한국어 처리 능력.<br/>**(-)** 유료 비용 발생. |

---

## 4. Infrastructure & Deployment

>복잡한 인프라 관리 대신 **관리형 서비스**와 **컨테이너 표준화**를 통해 운영 부담을 줄입니다.

| Technology | Selection Rationale | Pros & Cons |
| :--- | :--- | :--- |
| **Vercel** | **Frontend-Ops**: Next.js 개발팀이 만든 최적의 호스팅 환경.<br/>**CI/CD**: GitHub Push 시 자동 배포 및 프리뷰 환경 제공으로 개발 속도 향상. | **(+)** 설정 없는 배포, 글로벌 Edge Network.<br/>**(-)** 서버리스 함수 실행 시간 제한(Timeout) 존재. |
| **AWS-EC2** | **Long-Running**: AI 에이전트의 긴 작업 시간(Timeout 이슈)을 피하기 위해 백엔드는 Vercel 대신 VM 선택.<br/>**Control**: Docker 기반이므로 추후 확장 용이. | **(+)** 완전한 서버 제어 권한, 타임아웃 없음.<br/>**(-)** 보안 및 네트워크 직접 설정 필요. |
| **Docker** | **Consistency**: 로컬 개발 환경과 AWS 배포 환경을 일치시켜 환경 차이 문제 원천 차단.<br/>**Standard**: 추후 CI/CD 파이프라인 구축의 기반. | **(+)** 환경 종속성 제거, 손쉬운 배포.<br/>**(-)** 이미지 빌드 시간 소요. |
| **MongoDB** | **Flexible**: 대화 로그, 스킬 트리 등 구조가 가변적인 JSON 데이터 저장에 최적.<br/>**Managed**: Atlas 클라우드를 사용하여 유지보수 비용 절감. | **(+)** 유연한 스키마 변경, 초기 설정 불필요.<br/>**(-)** 복잡한 통계 쿼리 성능 열세. |

---

## 5. FAQ
> 기술적 성능 외에 개발 생산성, 비용 효율성 등 **비기능적 요소를 고려한 의사결정** 내역입니다.

### 1. 왜 Python 백엔드인가? (vs Node.js)
* **결정**: `FastAPI (Python)`
* **근거**: **단일 언어 전략**을 취했습니다. Node.js가 웹 생태계는 넓지만, 핵심인 AI 라이브러리(LangChain, PyTorch)는 Python이 주류입니다. 언어를 통일하여 **컨텍스트 스위칭 비용**과 **데이터 직렬화 오버헤드**를 줄였습니다.

### 2. 왜 프론트엔드를 Next.js로 하는가? (vs Streamlit)
* **결정**: `Next.js (React)`
* **근거**: **사용자 경험(UX)의 확장성**을 고려했습니다. Streamlit은 빠르지만 프로젝트의 핵심인 **상호작용 가능한 스킬 트리**와 **커스텀 채팅 UI**를 구현하기엔 제약이 큽니다. 포트폴리오로서의 시각적 완성도를 높이기 위해 선택했습니다.

### 3. 왜 프론트엔드를 AWS가 아닌 Vercel에 배포하는가?
* **결정**: `Vercel`
* **근거**: **개발자 경험(DX)과 배포 자동화**에 집중했습니다. AWS S3/CloudFront의 복잡한 설정 없이, Next.js에 최적화된 **Zero-Config CI/CD**를 통해 인프라 관리 부담을 최소화했습니다.

### 4. 왜 AWS를 선택했는가? (vs GCP, Azure)
* **결정**: `AWS (EC2)`
* **근거**: **비용 효율성**과 **표준성**을 택했습니다. 초기에는 **AWS Free Tier**를 활용하여 비용을 절감하고, 가장 보편적인 Docker 배포 환경을 구축하여 추후 확장성을 확보했습니다.

### 5. 왜 MongoDB를 선택했는가? (vs Firebase)
* **결정**: `MongoDB Atlas`
* **근거**: **데이터 구조 적합성**과 **관리 편의성**을 고려했습니다. Firebase보다 유연한 트리 구조 표현이 가능하며, **평생 무료 티어**(M0 Sandbox)를 통해 비용 부담 없이 비정형 대화 로그를 저장할 수 있습니다. 
