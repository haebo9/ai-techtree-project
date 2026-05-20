# Technical Decisions

TechTree v2.0.0의 주요 기술 선택과 그 이유를 정리한 문서입니다. 현재 기준은 **Next.js + FastAPI + OpenAI Realtime WebRTC + LangGraph + Docker/AWS**입니다.

0. [FAQ](#0-faq)
1. [Frontend](#1-frontend)
2. [Backend](#2-backend)
3. [AI Engine](#3-ai-engine)
4. [Model Usage](#4-model-usage)
5. [External Services](#5-external-services)
6. [Infrastructure](#6-infrastructure)

---

## 0. FAQ

### 1. 왜 Python 백엔드인가? (vs Node.js)

**결정**: `FastAPI`

LLM, LangGraph, Pydantic 등 AI 백엔드 생태계와 잘 맞습니다. 프론트엔드는 Next.js가 맡고, Python 백엔드는 세션 발급, 업로드 분석, 평가 리포트 같은 AI/데이터 흐름에 집중합니다.

### 2. 왜 Next.js인가? (vs Streamlit)

**결정**: `Next.js App Router`

TechTree는 대시보드가 아니라 브라우저 음성 면접 서비스입니다. WebRTC, 파일 업로드, sessionStorage, Push-to-Talk, 반응형 화면 제어가 필요하므로 React 기반 Next.js가 더 적합합니다.

### 3. 왜 Realtime을 백엔드 프록시하지 않는가?

**결정**: `Browser to OpenAI Realtime WebRTC`

음성 면접은 지연 시간이 곧 UX입니다. 브라우저가 OpenAI Realtime에 직접 연결하면 서버가 오디오 스트림을 중계하지 않아도 되고, 백엔드는 세션 준비와 종료 평가에 집중할 수 있습니다.

### 4. 왜 자동 VAD 대신 Push-to-Talk인가?

**결정**: `Space hold to talk`

면접에서는 지원자가 잠시 생각하는 침묵이 자연스럽습니다. 자동 VAD가 이를 답변 종료로 오해하지 않도록, 사용자가 Space를 누르는 동안만 마이크를 열고 손을 떼면 답변을 커밋합니다.

### 5. 왜 LangGraph를 유지하는가?

**결정**: `Realtime과 LangGraph 책임 분리`

Realtime은 면접 중 대화를 담당하고, LangGraph는 면접 전 컨텍스트 준비와 면접 후 평가를 담당합니다. 실시간 루프에 복잡한 그래프 로직을 끼우지 않아 지연과 책임 충돌을 줄입니다.

### 6. 왜 채용 공고를 LLM 생성에 맡기지 않는가?

**결정**: `사용자 제공 공고와 Tavily 결과만 사용`

공고는 회사명, 직무명, URL의 사실성이 중요합니다. LLM이 임의로 만든 공고는 리포트 신뢰도를 떨어뜨리므로, 공고 데이터는 사용자 입력 또는 검색 결과만 사용합니다.

### 7. 왜 Reflection/Policy는 fine-tuning이 아닌가?

**결정**: `Prompt memory`

면접 품질 개선에는 모델 파라미터 학습보다 운영 지침의 선별 주입이 더 빠르고 통제하기 쉽습니다. TechTree는 원문 대화를 장기 저장하지 않고 비식별 Reflection/Policy만 축약 저장해 다음 면접 프롬프트에 일부만 반영합니다.

### 8. 왜 MongoDB인가?

**결정**: `MongoDB / Atlas Vector Search`

Reflection/Policy처럼 형태가 변하는 운영 메모리를 저장하기 쉽고, Atlas Vector Search로 현재 면접과 유사한 지침을 찾을 수 있습니다. MongoDB가 없을 때는 JSONL fallback으로 로컬 개발을 이어갈 수 있습니다.

### 9. 왜 Docker 기반 직접 배포인가? (vs Vercel)

**결정**: `AWS EC2 + Docker Compose + Nginx`

Realtime 세션 준비, 백그라운드 리포트 생성, Nginx/Certbot 운영까지 한 서버에서 제어하기 위해 직접 배포를 선택했습니다. 로컬과 운영 환경도 Compose로 맞춥니다.

---

## 1. Frontend

프론트엔드는 입력 폼, 파일 업로드, Realtime 연결, Push-to-Talk 면접 UI, 완료 화면을 담당합니다.

| Technology | Usage | Note |
| :--- | :--- | :--- |
| **Next.js 16 App Router** | `/`, `/interview`, `/complete`, `/result`, `/debug` | 주요 화면은 브라우저 API를 쓰므로 client component입니다. `/result`는 legacy/manual report view입니다. |
| **React 19** | 면접 상태, transcript, WebRTC/DataChannel 이벤트 관리 | Realtime 이벤트 순서가 흔들릴 수 있어 `useRef` 기반으로 방어적으로 보존합니다. |
| **Tailwind CSS 4** | 반응형 UI 스타일 | 별도 UI 라이브러리 없이 서비스 화면에 맞춘 커스텀 스타일을 유지합니다. |
| **Browser APIs** | `RTCPeerConnection`, `getUserMedia`, `sessionStorage`, `FileReader` | WebRTC 연결과 Push-to-Talk UX의 핵심입니다. |
| **heic2any** | HEIC 공고 이미지 변환 | iPhone 캡처 이미지를 입력할 수 있게 합니다. |

현재 사용하지 않는 이전 설계 요소: `ReactFlow`, `Shadcn/ui`, `Streamlit`.

---

## 2. Backend

백엔드는 초대코드 인증, 업로드 분석, Realtime client secret 발급, 종료 평가, 이메일 발송을 담당합니다.

| Technology | Usage | Note |
| :--- | :--- | :--- |
| **FastAPI** | `/api/invite`, `/api/interview`, `/api/upload` | API 라우팅과 인증 dependency의 중심입니다. |
| **Pydantic / pydantic-settings** | 요청/응답 검증, 환경 변수 로딩 | `.env`, `.env.local`, `backend/.env`, `backend/.env.local`을 지원합니다. |
| **REST API** | 앱 제어면 | 실시간 음성은 WebRTC가 맡고, 서버는 세션/평가/메일 같은 명령형 흐름을 처리합니다. |
| **BackgroundTasks** | 리포트 생성과 이메일 발송 | 면접 종료 응답을 빠르게 돌려주기 위해 평가를 백그라운드로 넘깁니다. |
| **PyPDF2** | PDF 이력서 텍스트 추출 | 이미지 기반 PDF OCR은 현재 범위가 아닙니다. |

현재 사용하지 않는 이전 설계 요소: `SSE`, 자체 WebSocket 음성 서버.

---

## 3. AI Engine

AI 계층은 실시간 대화, 컨텍스트 준비, 구조화 평가, prompt memory로 나뉩니다.

| Technology | Usage | Note |
| :--- | :--- | :--- |
| **OpenAI Realtime API** | 음성 면접관 대화와 입력 음성 전사 | 브라우저에서 WebRTC로 직접 연결합니다. |
| **LangGraph** | 면접 전 manager, 면접 후 evaluator | 실시간 대화 루프 밖에서 상태 기반 작업을 처리합니다. |
| **LangChain / langchain-openai** | `ChatOpenAI`, structured output | 평가 리포트와 reflection 후보처럼 스키마가 필요한 작업에 사용합니다. |
| **Reflection Service** | Reflection/Policy 저장, 선택, outcome 기록 | 다음 면접 프롬프트에 관련 지침만 일부 주입합니다. |
| **Structured Output** | 평가 결과 필드 고정 | 이메일 템플릿과 리포트 화면이 기대하는 구조를 맞춥니다. |

운영 원칙:

- 최종 리포트의 핵심은 추천 공고가 아니라 대화 기반 평가 피드백입니다.
- 공고 데이터는 LLM이 만들지 않고 사용자 입력 또는 Tavily 결과만 사용합니다.
- Reflection/Policy는 면접관 프롬프트를 보조하는 운영 지침이며, 모든 세션에 전부 주입하지 않습니다.

---

## 4. Model Usage

코드에서 실제 호출되는 모델만 정리합니다. 가격은 변동이 잦으므로 문서에 고정하지 않고 운영 전 공식 가격표에서 확인합니다.

| Feature | Model | Purpose | Source |
| :--- | :--- | :--- | :--- |
| 실시간 음성 면접 | `gpt-realtime-mini-2025-12-15` | 저지연 음성 대화와 면접관 응답 | `backend/app/api/interview.py`, `frontend/app/interview/page.tsx`, `frontend/app/debug/page.tsx` |
| 입력 음성 전사 | `whisper-1` | 사용자 답변 transcript 생성 | `backend/app/api/interview.py` |
| 공고 텍스트/이미지 분석 | `gpt-5.4-nano` | 공고 요약, 직무명/요구역량 추출 | `backend/app/api/upload.py`, `backend/app/services/interview_manager.py` |
| LangGraph manager/evaluator | `gpt-4.1` | 면접 컨텍스트 판단, 평가 리포트 생성 | `backend/app/core/llm.py`, `backend/app/engine/nodes/` |
| Reflection 후보 생성 | `gpt-4.1` | 재사용 가능한 운영 지침 후보 추출 | `backend/app/services/reflection_service.py` |
| Reflection/Policy 검색 | `text-embedding-3-small` | 의미 기반 지침 검색 | `backend/app/core/config.py`, `backend/app/services/reflection_mongo_store.py` |

AI 모델을 쓰지 않는 기능:

- PDF 텍스트 추출: `PyPDF2`
- 채용 공고 검색: `Tavily API`
- 이메일 발송: `Resend API`
- 초대코드 인증: MongoDB 조회와 서명 쿠키
- Telegram 알림: `Telegram Bot API`

---

## 5. External Services

| Service | Usage | Note |
| :--- | :--- | :--- |
| **Tavily API** | `search_korean_job_postings` | 실제 공고 검색에만 사용합니다. API 키가 없거나 실패하면 빈 결과로 처리합니다. |
| **MongoDB / Atlas Vector Search** | Reflection/Policy, invite code | 운영 메모리와 초대코드를 저장합니다. |
| **Resend** | 이메일 리포트 발송 | 면접 종료 후 백그라운드 작업에서 HTML 리포트를 발송합니다. |
| **Telegram Bot API** | 운영 로그/알림 | 장애나 주요 이벤트 알림을 위한 선택 기능입니다. |

---

## 6. Infrastructure

| Technology | Usage | Note |
| :--- | :--- | :--- |
| **Docker Compose** | frontend, backend, nginx, certbot 통합 실행 | 로컬 smoke test와 운영 배포의 실행 방식을 맞춥니다. |
| **Next.js standalone** | frontend production image | Docker 이미지 크기와 실행 효율을 줄입니다. |
| **Nginx** | reverse proxy, SSL termination | `/`는 frontend, `/api/*`는 backend로 분기합니다. |
| **Certbot** | Let's Encrypt 인증서 | HTTPS 인증서 발급/갱신에 사용합니다. |
| **Environment Variables** | API key, DB URL, invite secret | secret은 코드에 넣지 않고 배포 환경에서 주입합니다. |
| **AWS EC2** | 운영 서버 | 현재 가이드는 `t3.small` 이상과 swap 사용을 권장합니다. |
| **Squarespace DNS / Elastic IP** | `techtree.haebo.pro` 연결 | Squarespace A 레코드가 EC2 Elastic IP를 가리킵니다. |

운영 원칙:

- 공개 진입 전 초대코드 인증을 요구합니다.
- 이력서/공고 분석과 면접 시작 API에도 인증 dependency를 적용합니다.
- API key, 인증서 private key, 업로드 원본은 저장소에 커밋하지 않습니다.
