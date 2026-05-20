# Project Structure

이 문서는 현재 배포 기준의 저장소 구조를 빠르게 파악하기 위한 요약입니다. 런타임 경로는 **Next.js + FastAPI + OpenAI Realtime WebRTC + LangGraph evaluator + ReflectionService**입니다.

```text
.
├── AGENTS.md
├── GUIDE.md                         # 로컬 실행, AWS EC2 Docker 배포 가이드
├── README.md                        # 프로젝트 소개
├── STRUCTURE.md                     # 현재 저장소 구조 요약
├── docker-compose.yml               # 운영 compose: backend/frontend build, nginx, certbot
├── docker-compose.local.yml         # 로컬 Docker smoke test
├── docker-compose.bootstrap.yml     # 최초 SSL 발급 전 HTTP bootstrap nginx 설정
├── .dockerignore
├── backend/
│   ├── Dockerfile                   # FastAPI backend image
│   ├── requirements.txt
│   ├── langgraph.json
│   ├── app/
│   │   ├── main.py                  # FastAPI entrypoint, CORS, /api router mount
│   │   ├── api/
│   │   │   ├── router.py            # /api router aggregation
│   │   │   ├── invite.py            # invite code verification/session/logout
│   │   │   ├── upload.py            # PDF parsing, job description analysis
│   │   │   └── interview.py         # Realtime client secret, async report, email
│   │   ├── core/
│   │   │   ├── config.py            # pydantic settings and env loading
│   │   │   ├── llm.py               # ChatOpenAI factory
│   │   │   └── logger.py            # app logging, optional Telegram alerts
│   │   ├── engine/
│   │   │   ├── graphs/              # LangGraph state/workflow
│   │   │   ├── nodes/               # manager/evaluator nodes
│   │   │   ├── prompts/             # Realtime interviewer and reflection prompts
│   │   │   └── tools/               # Tavily-backed job search helpers
│   │   ├── schemas_api/             # FastAPI request/response models
│   │   ├── services/
│   │   │   ├── interview_manager.py # session context, mode guidance, job analysis
│   │   │   ├── invite_service.py    # Mongo-backed invite auth
│   │   │   ├── reflection_service.py
│   │   │   └── reflection_mongo_store.py
│   │   └── source/                  # JSONL fallback for reflection/policy memory
│   ├── scripts/
│   │   ├── create_invite_code.py
│   │   └── setup_reflection_db.py
│   └── tests/
├── frontend/
│   ├── Dockerfile                   # Next.js standalone image
│   ├── app/
│   │   ├── page.tsx                 # invite auth, profile/resume/job input, product page
│   │   ├── interview/page.tsx       # OpenAI Realtime WebRTC interview
│   │   ├── complete/page.tsx        # async report/email completion screen
│   │   ├── result/page.tsx          # legacy/manual report view
│   │   ├── debug/page.tsx           # prompt and Realtime debug utility
│   │   ├── layout.tsx               # local fonts and app shell
│   │   └── globals.css              # global theme/font styles
│   ├── lib/
│   │   └── api.ts                   # /api base path helper
│   ├── public/
│   │   ├── font/                    # Gmarket Sans, Noto Sans KR
│   │   ├── logo/                    # service/tech logos
│   │   └── service/                 # service screenshots for home page
│   ├── next.config.ts               # standalone output, /api rewrite
│   ├── package.json
│   └── package-lock.json
├── nginx/
│   ├── default.conf                 # production HTTPS reverse proxy
│   ├── default.bootstrap.conf       # first certificate issue HTTP proxy
│   └── default.local.conf           # local reverse proxy
├── certbot/
│   ├── conf/                        # Let's Encrypt cert volume
│   └── www/                         # ACME webroot
└── docs/
    ├── README.md                    # documentation index
    ├── techtree-wiki.md             # full technical wiki
    ├── service_screens.md           # service screenshots and screen flow
    ├── mvp_and_plan.md              # MVP history and roadmap
    ├── user_flow.md                 # user/system flow
    ├── architecture.md              # versioned architecture notes
    ├── agent_workflow.md            # versioned AI workflow notes
    ├── tech_decisions.md            # technical decisions
    ├── references.md                # references, theme, fonts
    └── dev_log.md                   # development log
```

## Runtime Summary

- Frontend는 Next.js App Router 클라이언트 화면으로, 브라우저 API, 파일 업로드, WebRTC, sessionStorage를 사용합니다.
- Backend는 FastAPI `/api` 라우터로 초대코드, 업로드 분석, 면접 세션 시작, 종료 평가, 이메일 발송을 처리합니다.
- 실시간 음성 면접은 브라우저가 OpenAI Realtime에 WebRTC로 직접 연결하고, backend는 client secret과 프롬프트를 준비합니다.
- 면접 종료 후 평가는 LangGraph workflow가 수행하고, 이메일 리포트는 FastAPI background task에서 Resend로 발송합니다.
- Reflection/Policy는 모델 파라미터 학습이 아니라 비식별 운영 지침을 MongoDB 또는 JSONL에 저장한 뒤 다음 면접 프롬프트에 일부 주입하는 구조입니다.

## Documentation Map

- 서비스 소개와 빠른 실행은 [README.md](./README.md)에서 확인합니다.
- 실제 구축과 배포 절차는 [GUIDE.md](./GUIDE.md)를 기준으로 진행합니다.
- 제품과 기술 구조를 한 번에 이해하려면 [docs/README.md](./docs/README.md)의 추천 읽기 순서를 따릅니다.
- 현재 코드 구조와 문서 내용이 다를 때는 실제 런타임 코드와 배포 compose 설정을 우선합니다.
