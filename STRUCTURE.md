# Project Structure

```
.
├── STRUCTURE.md                    # 프로젝트 구조 설명
├── docker-compose.yml              # 배포용 Docker 설정
├── docker-compose.local.yml        # 로컬 개발용 Docker 설정
├── README.md                       # 메인 설명서
├── backend/                        # [Backend] 파이썬 서버
│   ├── app/
│   │   ├── main.py                 # 앱 진입점 (FastAPI)
│   │   │
│   │   ├── api/                    # [REST API] 웹 클라이언트용 (FastAPI Router)
│   │   │   ├── router.py           # Unified router
│   │   │   ├── endpoints/          # API Endpoints (stateless_chat, stateful_chat, techtree)
│   │   │
│   │   ├── api_mcp/                # [MCP API] AI 에이전트용 (MCP Server)
│   │   │   ├── server.py           # MCP 서버
│   │   │   ├── tools.py            # MCP Tools 등록부
│   │   │
│   │   ├── engine/                 # [Engine] 핵심 비즈니스 로직 (Core)
│   │   │   ├── agents/             # - AI 면접관/평가자 구현체 (Brain)
│   │   │   ├── graphs/             # - LangGraph 실행 흐름 (Flow)
│   │   │   ├── tools/              # - 검색/분석 도구 모음 (Skills)
│   │   │   └── prompts/            # - 프롬프트 템플릿
│   │   │
│   │   ├── core/                   # [Infra] 설정, DB 연결, 로깅, 통합 LLM
│   │   ├── services/               # [Service] DB CRUD 로직
│   │   ├── schemas_api/            # [DTO] API 요청/응답 모델
│   │   ├── schemas_db/             # [Model] DB 스키마
│   │   └── source/                 # [Static] 트랙/서베이 정적 데이터
│   │
│   └── tests/                      # 테스트 코드
│
├── frontend/                       # [Frontend] 웹 애플리케이션 (Next.js)
│   ├── src/                        # 메인 소스코드
│   ├── public/                     # 정적 에셋
│   └── legacy_streamlit/           # (Legacy) Streamlit 앱
│
├── docs/                           # [Docs] 문서 보관소
│   ├── 1_prd/                      # 기획서 (Spec, Persona)
│   ├── 2_design/                   # 설계문서 (Architecture, DB)
│   └── 3_knowledge/                # 기술 검토 및 참고 자료
│
└── nginx/                          # Nginx 게이트웨이 설정
```
