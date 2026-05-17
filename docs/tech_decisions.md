# Technical Decisions

> **TechTree** 개발을 위한 기술 스택 선정 및 아키텍처 의사결정 문서입니다.
> 현재 작업 기준은 **Next.js + FastAPI + OpenAI Realtime(WebRTC) + LangGraph** 기반의 AI 모의면접 서비스입니다.
> **Docker Compose**와 **Nginx**를 활용하여 전체 스택이 컨테이너화되어 배포되어 있으며, SSL(HTTPS) 환경에서 안정적으로 운영됩니다.

0. [FAQ](#0-faq)
1. [Frontend Architecture](#1-frontend-architecture)
2. [Backend Architecture](#2-backend-architecture)
3. [AI & Intelligence Engine](#3-ai--intelligence-engine)
4. [AI Model Usage](#4-ai-model-usage)
5. [External Services & Storage](#5-external-services--storage)
6. [Infrastructure & Deployment](#6-infrastructure--deployment)

---

## 0. FAQ

### 1. 왜 Python 백엔드인가? (vs Node.js)

**결정**: `FastAPI (Python)`

**근거**: LLM 호출과 LangGraph 기반의 AI 오케스트레이션 라이브러리 생태계가 가장 풍부하여 개발 생산성을 극대화할 수 있습니다. 프론트엔드는 Next.js로 분리하고 백엔드는 AI 로직과 데이터 처리에만 집중할 수 있는 구조를 채택했습니다.

### 2. 왜 프론트엔드를 Next.js로 하는가? (vs Streamlit)

**결정**: `Next.js (React)`

**근거**: 실시간 WebRTC 연결과 Push-to-Talk와 같은 복합적인 브라우저 인터랙션을 안정적으로 제어하기 위해 React 생태계의 Next.js를 선택했습니다. 단순한 대시보드를 넘어 사용자 흐름에 맞춘 정교한 면접 UX와 결과 리포트 화면을 구현하기에 최적입니다.

### 3. 왜 Realtime은 백엔드 프록시가 아니라 브라우저 WebRTC로 연결하는가?

**결정**: `OpenAI Realtime WebRTC`

**근거**: 음성 면접의 핵심인 초저지연(Low-latency) 환경을 제공하기 위해 브라우저와 OpenAI Realtime을 서버를 거치지 않고 직접 연결합니다. 이를 통해 응답 속도를 최적화하고 서버의 오디오 처리 부하를 최소화하여 동시 접속 안정성을 높였습니다.

### 4. 왜 LangGraph를 사용하는가?

**결정**: `LangGraph 사용`

**근거**: 실시간 대화는 OpenAI Realtime이 담당하지만, 면접 종료 후의 복잡한 평가 로직과 비동기 리포트 생성은 상태 관리가 용이한 LangGraph가 수행합니다. 기존의 상태 구조를 활용하여 면접 단계별 워크플로우를 안정적으로 제어하고 확장할 수 있습니다.

### 5. 왜 채용 공고/공고 검색 데이터를 LLM 생성에 맡기지 않는가?

**결정**: `사용자 제공 공고와 Tavily 검색 결과만 면접 컨텍스트/보조 데이터로 사용`

**근거**: 채용 공고는 실제 모집 현황과 정확한 URL 정보가 중요하므로 LLM의 환각(Hallucination) 위험을 배제해야 합니다. 현재 제품의 핵심 리포트는 점수, 강점, 개선점, 상세 Q&A, 말투/자기소개/직무 적합도 피드백이며, 공고 데이터는 면접 맥락과 도구 실행 기록을 보조하는 용도로만 다룹니다.

### 6. 왜 MongoDB를 선택했는가?

**결정**: `MongoDB / Atlas Vector Search`

**근거**: 운영 정책(Policy)이나 자가 성찰(Reflection) 데이터처럼 스키마가 수시로 변하는 비정형 데이터를 저장하고 관리하기에 유연한 MongoDB가 적합합니다. 또한 Atlas Vector Search를 활용하면 과거 가이드라인 중 현재 맥락과 유사한 데이터를 의미론적으로 빠르게 탐색할 수 있습니다.

### 7. 왜 Vercel 같은 매니지드 서비스 대신 Docker 기반 직접 배포를 선택했는가?

**결정**: `AWS EC2 + Docker Compose + Nginx`

**근거**: 긴 실행 시간이 필요한 AI 추론 세션과 백그라운드 리포트 생성 작업을 타임아웃 제한 없이 안정적으로 수행하기 위해 직접 서버를 제어하는 Docker 배포를 선택했습니다. 인프라 확장성이 뛰어나며 전체 스택을 컨테이너화하여 로컬과 서버 간의 환경 일관성을 보장합니다.

### 8. 왜 자동 음성 감지(VAD) 대신 Push-to-Talk(PTT) 방식을 사용하는가?

**결정**: `사용자 수동 커밋 (Space 키 홀드)`

**근거**: 지원자가 답변 도중 생각을 위해 잠시 멈추는 것을 끝으로 오인하지 않도록 사용자가 직접 입력 시점을 제어하는 방식을 채택했습니다. 이를 통해 불필요한 잡음 유입을 차단하고 OpenAI Realtime API에 가장 깨끗한 오디오 데이터를 전달하여 전사 정확도를 높였습니다.

---
---

## 1. Frontend Architecture

> 프론트엔드는 면접 준비 입력, Realtime WebRTC 연결, push-to-talk 음성 답변, 결과 리포트 표시를 담당합니다.

| Technology | Current Usage | Decision Notes |
| :--- | :--- | :--- |
| **Next.js 16 App Router** | `/`, `/interview`, `/result`, `/complete`, `/debug` 페이지 구성 | 파일 기반 라우팅과 클라이언트 컴포넌트를 활용합니다. WebRTC, localStorage, FileReader, mediaDevices 사용 때문에 주요 화면은 클라이언트 컴포넌트입니다. |
| **React 19** | 면접 상태, transcript, WebRTC peer connection, data channel 이벤트 관리 | 실시간 이벤트 순서가 흔들릴 수 있으므로 `useRef` 기반 상태 보존과 방어적 이벤트 처리를 사용합니다. |
| **Tailwind CSS 4** | 화면 스타일링과 반응형 UI 구성 | 별도 컴포넌트 라이브러리 없이 현재 화면에 맞춘 경량 스타일을 유지합니다. |
| **Browser APIs** | `RTCPeerConnection`, `getUserMedia`, `localStorage`, `FileReader` | OpenAI Realtime 연결과 push-to-talk UX의 핵심입니다. 마이크 트랙은 기본 비활성화하고 사용자가 Space를 누르는 동안만 활성화합니다. |
| **pdfjs-dist / heic2any** | 이력서 PDF 처리 보조, HEIC 채용 공고 이미지 변환 | 업로드 가능한 문서/이미지 입력 범위를 넓히기 위한 프론트 보조 도구입니다. |

현재 사용하지 않는 이전 설계 요소:

- `ReactFlow`: 현재 패키지 의존성에 없으며 스킬 트리 시각화는 현재 MVP의 핵심 런타임 경로가 아닙니다.
- `Shadcn/ui`: 현재 패키지 의존성에 없고, UI는 Tailwind 기반 커스텀 구현입니다.
- `Streamlit`: 이전 프로토타입 설계 요소이며, 현재는 Next.js로 전면 교체되었습니다.

---

## 2. Backend Architecture

> 백엔드는 FastAPI API 서버, OpenAI Realtime 세션 발급, 업로드 분석, 채용 검색 도구, 평가 리포트 생성을 담당합니다.

| Technology | Current Usage | Decision Notes |
| :--- | :--- | :--- |
| **FastAPI** | `/api/interview`, `/api/upload` 라우터 제공 | Pydantic 스키마와 Python AI 생태계 연동이 좋아 현재 백엔드의 중심으로 사용합니다. |
| **Pydantic / pydantic-settings** | API 요청/응답 검증, 환경 변수 로딩 | `.env`, `.env.local`, `backend/.env`, `backend/.env.local`을 통해 로컬/배포 환경을 분리합니다. |
| **REST API** | 면접 시작, 검색 도구 실행, 면접 종료, 이메일 발송, 업로드 분석 | 브라우저와 백엔드 사이의 애플리케이션 제어면은 REST로 유지합니다. 실시간 음성 스트림은 OpenAI Realtime WebRTC가 담당합니다. |
| **BackgroundTasks** | 면접 종료 후 리포트 생성 및 이메일 발송 | 사용자가 면접 종료 응답을 빠르게 받도록 리포트 생성 작업을 백그라운드로 넘깁니다. |
| **PyPDF2** | 업로드된 PDF 이력서 텍스트 추출 | 텍스트 기반 PDF만 처리합니다. 이미지 기반 PDF OCR은 현재 범위가 아닙니다. |

현재 사용하지 않는 이전 설계 요소:

- **SSE**: 현재 면접 런타임은 SSE 스트리밍이 아니라 OpenAI Realtime WebRTC입니다.
- **WebSocket 서버 직접 운영**: 양방향 음성 통신은 자체 WebSocket 서버가 아니라 OpenAI Realtime과 브라우저 WebRTC 연결로 처리합니다.

---

## 3. AI & Intelligence Engine

> TechTree의 AI 계층은 실시간 면접 진행, 채용 공고 분석, 최종 평가, reflection 기반 프롬프트 개선으로 나뉩니다.

| Technology | Current Usage | Decision Notes |
| :--- | :--- | :--- |
| **OpenAI Realtime API** | 음성 면접관 대화, 음성/텍스트 응답, tool call 판단 | 면접 중 저지연 음성 UX가 가장 중요하므로 브라우저에서 WebRTC로 직접 연결합니다. |
| **LangChain / langchain-openai** | `ChatOpenAI`, structured output, tool binding | 평가 리포트와 reflection 후보 생성처럼 구조화된 결과가 필요한 작업에 사용합니다. |
| **LangGraph** | 면접 상태 저장, 평가 워크플로우 실행, `/chat` 호환 경로 | Realtime이 실제 면접 진행을 담당하지만, 종료 후 평가와 상태 기반 워크플로우에는 LangGraph를 유지합니다. |
| **Reflection Service** | 과거 면접 결과에서 prompt guideline 후보 생성 및 선택 | `short`, `long`, `common` scope를 기준으로 다음 면접 프롬프트에 운영 지침을 주입합니다. |
| **Structured Output** | 평가 리포트와 reflection 생성 결과 스키마 고정 | 리포트 화면과 이메일 템플릿이 기대하는 필드 구조를 안정적으로 맞추기 위해 사용합니다. |

운영 원칙:

- 공고 데이터는 LLM이 지어내지 않고, Tavily 검색 결과 또는 사용자가 제공한 공고에서만 사용합니다.
- Realtime 프롬프트는 `short`와 `long`의 면접 목적 차이를 유지하고, reflection/policy는 이를 보조하는 운영 지침으로만 반영합니다.
- 최종 리포트의 핵심 결과물은 추천 공고가 아니라 대화 기반 평가 피드백입니다.

---

## 4. AI Model Usage

> 2026-05-13 기준 코드에서 실제 호출되는 AI 모델만 정리합니다. 모델명은 코드에 하드코딩된 값 또는 설정 기본값을 기준으로 합니다. 비용은 OpenAI 공식 Standard pricing 기준이며, 별도 표기가 없으면 1M tokens 단위입니다.

| Feature | Model | Purpose | Cost | Source |
| :--- | :--- | :--- | :--- | :--- |
| 실시간 음성 면접 세션 | `gpt-realtime-mini` | **저지연 S2S WebRTC 대화 및 실시간 Function Calling 제어**<br/>→ 면접 UX 최적화를 위한 Realtime 전용 mini 모델 활용 | Audio Input: $10.00<br/>Audio Output: $20.00<br/>Text Input: $0.60<br/>Text Output: $2.40 | `backend/app/api/interview.py`<br/>`frontend/app/interview/page.tsx`<br/>`frontend/app/debug/page.tsx` |
| 실시간 입력 음성 전사 | `whisper-1` | **실시간 오디오 스트림 STT(Speech-to-Text) 및 텍스트 로그 보존**<br/>→ OpenAI Realtime 인터페이스 표준 모델 활용 | Transcription: $0.006 / minute | `backend/app/api/interview.py` |
| 채용 공고 텍스트/이미지 직무명 추출 | `gpt-5.4-nano` | **멀티모달 Vision 기반 JD 개요 분석 및 엔티티(Entity) 추출**<br/>→ GPT-5.4 Nano의 경량 멀티모달 처리 성능 활용 | Input: $0.20<br/>Output: $1.25 | `backend/app/api/upload.py` |
| 면접 시작 전 채용 공고 이미지 분석 | `gpt-5.4-nano` | **Vision 기반 구조화 요약(Structured Output) 및 요구역량 매핑**<br/>→ 대량 텍스트 요약 및 이미지 파싱 효율성 고려 | Input: $0.20<br/>Output: $1.25 | `backend/app/api/interview.py` |
| LangGraph 면접관 노드 | `gpt-4.1` | **RESTful 에이전트 추론(Reasoning) 및 복합 툴 제어**<br/>→ 안정적인 Instruction Following 및 고품질 질문 생성 | Input: $2.00<br/>Output: $8.00 | `backend/app/core/llm.py`<br/>`backend/app/engine/nodes/interviewer.py` |
| 최종 면접 평가 리포트 | `gpt-4.1` | **긴 컨텍스트(Context) 분석 및 정밀 피드백 구조화 생성**<br/>→ 정교한 한국어 평가 및 복합 스키마 출력 보장 | Input: $2.00<br/>Output: $8.00 | `backend/app/core/llm.py`<br/>`backend/app/engine/nodes/evaluator.py` |
| Reflection 후보 생성 | `gpt-4.1` | **자가 성찰(Self-Reflection) 기반 운영 정책(Policy) 후보 추출**<br/>→ 재사용 가능한 가이드라인 선별을 위한 고성능 추론 | Input: $2.00<br/>Output: $8.00 | `backend/app/core/llm.py`<br/>`backend/app/services/reflection_service.py` |
| Reflection/Policy 벡터 검색 | `text-embedding-3-small` | **의미론적 검색(Semantic Search)을 위한 고밀도 벡터 임베딩 생성**<br/>→ 대규모 텍스트 유사도 검색 효율성 확보 | $0.02 / 1M tokens<br/>Batch: $0.01 / 1M | `backend/app/core/config.py`<br/>`backend/app/services/reflection_mongo_store.py` |

차기 버전 모델 개선 계획
- 세션/UX 개선: whisper-1 대기 시간을 활용한 '사전 키워드 힌트' 도입 또는 `gpt-realtime-whisper` 모델로 변경
- 운영 비용 절감: 기존 LangGraph의 gpt-4.1 노드들을 `gpt-5.4-mini(or -nano)`로 전면 교체
- 평가 품질 극대화: 심층 분석이 필요한 최종 평가 노드에만 `gpt-5.4`를 전략적으로 배치

AI 모델을 사용하지 않는 주요 기능:

- PDF 이력서 텍스트 추출: `PyPDF2` 기반 파싱이며 별도 AI 모델을 호출하지 않습니다.
- 채용 공고 검색: `Tavily API`를 직접 호출하며 OpenAI 모델을 사용하지 않습니다.
- 이메일 발송: `Resend API`를 사용하며 AI 모델을 호출하지 않습니다.
- 초대코드 인증: MongoDB 조회와 서명된 세션 쿠키 검증으로 처리하며 AI 모델을 호출하지 않습니다.
- 텔레그램 알림/로깅: `Telegram Bot API` 구조이며 AI 모델을 호출하지 않습니다.

---

## 5. External Services & Storage

> 외부 서비스는 모델 기능과 운영 기능을 분리해 사용합니다.

| Service | Current Usage | Decision Notes |
| :--- | :--- | :--- |
| **Tavily API** | `search_job_postings` 도구와 면접 시작 전 추천 공고 탐색 | 채용 공고 추천은 실제 검색 결과 기반이어야 하므로 LLM 생성 대신 검색 API를 사용합니다. API 키가 없거나 검색 실패 시 구조화된 빈 결과/trace를 반환합니다. |
| **MongoDB / Atlas Vector Search** | reflection/policy 저장과 선택적 벡터 검색, 초대코드 저장 | 로컬 JSONL 저장소와 Mongo 저장소를 함께 고려하는 구조입니다. Atlas Vector Search가 가능하면 embedding 기반 유사 지침 검색을 사용합니다. 초대코드는 `invite_codes` 컬렉션에 `code`, `name`, `status`, `use_max`, `use_count`만 저장합니다. |
| **Resend** | 최종 면접 리포트 이메일 발송 | 면접 종료 후 백그라운드 작업에서 평가 결과를 HTML 이메일로 발송합니다. |
| **Telegram Bot API** | 운영 로그/초대코드 인증 알림 구조 | 배포 운영에서 장애나 주요 이벤트 알림에 사용할 수 있도록 설정값과 logger 구조를 유지합니다. 초대코드 인증 성공 시 전체 코드, 관리용 이름, 상태, 사용 횟수를 전송합니다. |

---

## 6. Infrastructure & Deployment

> TechTree는 **Docker Compose**를 기반으로 배포되며, **Nginx**가 리버스 프록시 및 정적 자산 서빙을 담당합니다.

| Technology | Status | Decision Notes |
| :--- | :--- | :--- |
| **Docker Compose** | 프론트엔드(Next.js), 백엔드(FastAPI), Nginx 통합 운영 | 컨테이너화를 통해 환경 일관성을 보장하며, `depends_on`을 통해 서비스 의존성을 관리합니다. |
| **Next.js (Standalone)** | `output: 'standalone'` 빌드 모드 사용 | Docker 이미지 크기를 최적화하고 프로덕션 환경에서의 실행 효율을 극대화합니다. |
| **Nginx** | Reverse Proxy 및 SSL Termination | 포트 `80/443`을 관리하며 프론트엔드(`:3000`)와 API(`:8000`) 경로를 분기 처리합니다. |
| **Certbot** | Let's Encrypt 기반 자동 SSL 갱신 | 주기적인 인증서 갱신을 통해 보안 연결을 유지합니다. |
| **Environment Variables** | `.env` 및 `docker-compose.yml` 관리 | API Key, DB URL, CORS 설정 등을 환경 변수로 주입하여 보안 및 유연성을 확보합니다. |
| **AWS EC2** | t3.medium 이상급 인스턴스 권장 | 음성 처리 및 LangGraph 워크플로우의 안정적 수행을 위해 적정 리소스를 할당합니다. |

운영 및 배포 관리 원칙:

- **Zero-Downtime Deployment**: 새로운 이미지 빌드 시 `docker-compose up -d --build`를 통해 서비스 중단을 최소화합니다.
- **CORS Management**: 백엔드 API는 허용된 도메인(`CORSMiddleware`)에 대해서만 요청을 허용합니다.
- **Logging**: Docker 로그 시스템 및 필요시 Telegram Bot 알림을 연동하여 시스템 상태를 모니터링합니다.
- **Access Control**: 공개 서비스 진입 전 초대코드 인증을 요구하며, 이력서/공고 분석과 면접 시작 API에도 인증 dependency를 적용합니다.
- **Secret Management**: 모든 API Key는 절대 코드에 포함하지 않으며, 배포 환경의 환경 변수로만 관리합니다.
