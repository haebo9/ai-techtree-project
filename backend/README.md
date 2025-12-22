# Backend

## Directory Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 진입점 (App 초기화, 미들웨어 설정)
│   ├── core/                   # 핵심 설정 (환경변수, DB 연결 객체)
│   │   ├── config.py           # .env 로드 및 설정 관리
│   │   ├── database.py         # MongoDB 연결 (Motor - Async)
│   │   ├── exceptions.py       # 커스텀 예외 처리
│   │   └── logging.py          # 로깅 설정
│   ├── api/                    # API 엔드포인트 계층
│   │   ├── deps.py             # 의존성 주입 (DB 세션, User)
│   │   └── v1/
│   │       ├── router.py       # API 라우터 통합
│   │       └── endpoints/
│   │           ├── mcp.py      # PlayMCP 연동용 SSE 엔드포인트
│   │           └── users.py    # 유저 관리 API
│   ├── models/                 # DB 모델 (MongoDB Document 구조 정의)
│   │   ├── common.py           # 공통 모델 (ObjectId 등)
│   │   ├── user.py             # User Collection (Skill Tree 포함)
│   │   ├── interview.py        # Interview Collection
│   │   ├── question.py         # Question Collection
│   │   ├── track.py            # Track Collection
│   │   └── skill.py            # Skill Collection
│   ├── schemas/                # API 스키마 (DTO, Request/Response 검증)
│   │   ├── common.py
│   │   └── interview.py
│   ├── services/               # 비즈니스 로직 계층 (DB CRUD, 단순 로직)
│   │   └── interview_service.py
│   └── ai/                     # AI/LangChain 핵심 로직
│       ├── agents/             # 개별 AI 에이전트 정의 (Interviewer, Evaluator)
│       │   ├── interviewer.py
│       │   └── evaluator.py
│       ├── graphs/             # LangGraph 오케스트레이터 정의
│       │   └── workflow.py
│       ├── tools/              # LangChain Tools (MCP Tool로도 활용 가능)
│       └── prompts/            # 프롬프트 템플릿 관리
│           └── default.py
├── tests/                      # 테스트 코드 (Pytest)
├── .env                        # 환경 변수 (API Key, DB URI)
├── .gitignore
├── Dockerfile                  # 배포용 Docker 설정
└── requirements.txt            # 의존성 패키지 목록
```