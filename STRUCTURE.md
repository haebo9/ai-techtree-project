# Project Structure

```
.
├── STRUCTURE.md                    # 프로젝트 구조 설명 (이 파일)
├── README.md                       # 메인 설명서
├── dev_log.md                      # 개발 일지 및 변경 이력
├── Dockerfile                      # 통합 리소스용 빌드 파일 (FastAPI, Streamlit, LangGraph)
├── docker-compose.yml              # [Production] 배포용 Docker 설정 (SSL 포함)
├── docker-compose.local.yml        # [Development] 로컬 개발용 Docker 설정
├── certbot/                        # [SSL] Let's Encrypt 인증서 관리용 볼륨
│
├── backend/                        # [Backend/Interface] 파이썬 통합 저장소
│   ├── app/
│   │   ├── main.py                 # FastAPI 앱 진입점
│   │   │
│   │   ├── api/                    # [FastAPI] REST API (통합 라우터)
│   │   │   └── router.py           # Endpoint 관리 (현재 슬림화/MCP 중심)
│   │   │
│   │   ├── api_mcp/                # [MCP] AI 에이전트용 (Kakao MCP Player 등)
│   │   │   ├── server.py           # FastMCP 서버 실행 (Port 8200)
│   │   │   └── tools.py            # MCP 전용 Tools (TechTree, Trend 등)
│   │   │
│   │   ├── engine/                 # [Core] 핵심 비즈니스 로직 및 워크플로우
│   │   │   ├── agents/             # - AI 에이전트 구현체 (Persona)
│   │   │   ├── graphs/             # - LangGraph 실행 흐름 (State, Graph)
│   │   │   ├── tools/              # - 핵심 기능 도구 모음 (Function, Schema)
│   │   │   └── prompts/            # - 시스템 프롬프트 템플릿
│   │   │
│   │   ├── core/                   # [Infra] 설정(Config), DB 연결, 로깅, LLM 초기화
│   │   ├── services/               # [Service] DB CRUD 및 비즈니스 보조 로직
│   │   ├── schemas_api/            # [DTO] API 요청/응답 모델
│   │   ├── schemas_db/             # [Model] MongoDB 스키마 정의
│   │   └── source/                 # [Static] 트랙, 설문, 이미지 등 정적 리소스
│   │
│   ├── langgraph.json              # LangGraph Studio/Server 설정
│   ├── streamlit_dashboard.py      # [Frontend] 현재 메인 사용자 인터페이스 (Streamlit)
│   ├── scripts/                    # DB 초기화 및 데이터 마이그레이션 스크립트
│   └── tests/                      # 단위 및 통합 테스트 코드
│
├── frontend/                       # [Frontend] (Next.js 준비용 빈 폴더 - 미래 확장 계획)
│
├── docs/                           # [Docs] 공식 문서 보관소
│   ├── 1_prd/                      # 기획서 (Product Spec, User Flow)
│   ├── 2_design/                   # 설계문서 (Arch, DB Schema, Agent Flow)
│   └── 3_knowledge/                # 기술 검토 및 MCP 참고 자료
│
└── nginx/                          # Nginx 게이트웨이 및 리버스 프록시 설정
    ├── default.conf                # 배포용 Nginx 설정 (Certbot 연동)
    └── default.local.conf          # 로컬용 Nginx 설정
```
