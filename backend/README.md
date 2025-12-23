# Backend

## Directory Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                         # FastAPI 진입점 (App 초기화, 미들웨어 설정)
│   ├── core/                           # 핵심 설정 (환경변수, DB 연결 객체)
│   │   ├── config.py                       # .env 로드 및 설정 관리
│   │   ├── database.py                     # MongoDB 연결 (Motor - Async)
│   │   ├── exceptions.py                   # 커스텀 예외 처리
│   │   └── logging.py                      # 로깅 설정
│   ├── api/                            # API 엔드포인트 계층
│   │   ├── deps.py                     # 의존성 주입 (DB 세션, User)
│   │   └── v1/                             # API 버전
│   │       ├── router.py                       # API 라우터 통합
│   │       └── endpoints/                  # API 엔드포인트
│   │           ├── mcp.py                      # PlayMCP 연동용 SSE 엔드포인트
│   │           └── users.py                    # 유저 관리 API
│   ├── db_schemas/                     # DB 데이터 구조 (MongoDB)
│   │   ├── common.py                       # 공통 설정 (ObjectId 처리 등)
│   │   ├── user.py                         # 유저 정보 + 개인별 스킬트리 상태
│   │   ├── interview.py                    # 면접 대화 로그 & 평가 결과표
│   │   ├── question.py                     # 면접 문제 은행 (질문 & 모범답안)
│   │   ├── track.py                        # 직무별 로드맵 커리큘럼 (Backend Basic 등)
│   │   └── skill.py                        # 기술 상세 정보 (아이콘, 설명 등)
│   ├── api_schemas/                    # API 스키마 (DTO, Request/Response 검증)
│   │   ├── common.py                       # 공통 응답 모델 (에러, 성공 메시지 등)
│   │   └── interview.py                    # 면접 관련 유효성 검사
│   ├── services/                       # 비즈니스 로직 계층 (DB CRUD, 단순 로직)
│   │   └── interview_service.py            # 면접 진행 관리 및 상태 업데이트
│   └── ai/                             # AI/LangChain 핵심 로직
│       ├── agents/                         # 개별 AI 에이전트 정의
│       │   ├── interviewer.py                  # 면접관 페르소나 및 대화 로직
│       │   └── evaluator.py                    # 답변 평가 및 점수 산정 로직
│       ├── graphs/                         # LangGraph 오케스트레이터
│       │   └── workflow.py                     # 에이전트 간 순서 및 분기 처리
│       ├── tools/                          # LangChain Tools (MCP 호환)
│       └── prompts/                        # 프롬프트 템플릿 관리
│           └── default.py
├── tests/                              # 테스트 코드 (Pytest)
├── .env                                # 환경 변수 (API Key, DB URI)
├── .gitignore
├── Dockerfile                          # 배포용 Docker 설정
└── requirements.txt                    # 의존성 패키지 목록
```