# Dev Log
>Dev log 문서는 개발 과정을 기록하기 위한 로그입니다. 색깔 태그를 통해 로그의 성격을 구분합니다.
> * 🔵 **Docs** : 기획, 설계, 문서 작성
> * 🟠 **FE** : 프론트엔드 (Next.js, UI)
> * 🟢 **BE** : 백엔드 (FastAPI, DB)
> * 🟣 **AI** : 인공지능 (Langchain, LLM)
> * ⚪️ **Infra** : 배포(AWS, Vercel), 환경 설정, CI/CD
> * 🔴 **Project** : 프로젝트 초기화, 릴리즈, 마일스톤 

> **+ Category** : **Feat**(새로운 기능), **Fix**(수정), **Refactor**(개선), **Add**(추가), **Update**(갱신), **Remove**(삭제), **Init**(초기화)

---
## 2026년 5월 
| Date | Tag | Category | Details |
|:---:|:---:|:---:|:---|
| **26.05.14(목)** | 🟢 | **Fix** | 배포를 위해 전체적인 구조 점검 및 에러 수정 | 
| **26.05.13(수)** | ⚪️ | **Feat** | AWS EC2 준비, 도커 파일 준비 | 
| | 🟢 | **Feat** | 초대코드 검증 및 세션 설정 기능 개발 (DB: `invite_codes` 컬렉션 생성) | 
| | 🔵 | **Add** | AI 모델 설계, 배포 환경, 기술 스택 등에 대한 내용 문서화 | 
| **26.05.12(화)** | 🟣 | **Fix** | 심층면접의 Reflection 결과가 면접 피드백에 반영되지 않는 문제 해결 |
| **26.05.11(월)** | 🟣 | **Feat** | `빠른 면접 및 심층 면접 모드` 도입, Reflection 데이터 기반 시맨틱 검색 구현 |
| | 🟢 | **Feat** | 최종 리포트 비동기 발송 처리 및 `MongoDB` 데이터 저장 로직 고도화 |
| | 🟢 | **Fix** | 자체 `QA`를 진행하여 면접 생성 시 발생하는 여러 오류 수정 및 개선 |
| **26.05.09(토)** | 🟣 | **Feat** | 면접 자동 종료 및 AI 자기 비판(`Self-Reflection`) 기반 피드백 고도화 |
| | 🟣 | **Feat** | 채용 공고 추천 품질 개선 및 검색 실패 시 `Fallback` 로직 구현 |
| | 🟠 | **Update** | 메인 UI 배치 최적화 |
| **26.05.08(금)** | 🟣 | **Feat** | 이력서/JD 이미지 분석 기반 면접 기능 및 드래그 앤 드롭 업로드 구현 |
| | 🟢 | **Feat** | AI 면접 결과 리포트 자동 생성 및 이메일 전송(`Resend`) 연동 |
| | 🟠 | **Update** | 사용자 정보 입력 UI 추가 |
| **26.05.07(목)** | 🔴 | **Init** | 기존 개발 과정 초기화 및 `v2.0` 아키텍처 재설계 |
| | 🟣 | **Feat** | `OpenAI Realtime(S2S)` 도입 및 실시간 음성 면접 로직 구현 |
| | 🟠 | **Feat** | 프론트엔드 메인 화면 초기화 및 면접 인터페이스 구현 |


## 2026년 3월
| Date | Tag | Category | Details |
|:---:|:---:|:---:|:---|
| **26.03.23(월)** | 🟣 | **Refactor** | LangGraph 워크플로우 점검, `Chat` 노드 구현 |
| **26.03.14(토)** | 🟣 | **Feat** | `quiz_chat` 노드 추가 및 연결 (퀴즈 진행 중 힌트 기능) |
| **26.03.13(금)** | 🟣 | **Refactor** | 랭그래프 구조 정리 및 연결 (Supervisor/Quiz Route) |
| **26.03.12(목)** | 🟣 | **Feat** | `v1.2` 랭그래프 `sub-agent` 구조 구현 |
| **26.03.06(금)** | 🔵 | **Add** | `v1.1` 아키텍처 제작(`draw.io`) 및 관련 문서에 반영 |
| **26.03.05(목)** | 🔵 | **Add** | `v1.2`을 위한 LangGraph workflow 설계, `v1.0` 아키텍처 제작(`draw.io`) |
|  | 🟢 | **Fix** | API 연결 에러 수정 및 테스트 완료 (`checkpointer` 구현) |
| **26.03.04(수)** | 🟢 | **Feat** | Debug용 Next.js 화면 구현 및 API 명세 문서 작성 |
| **26.03.03(화)** | 🟢 | **Feat** | `FastAPI` router 구현 및 `Next.js` 기본 화면과 연결 테스트 완료 |
| **26.03.02(월)** | 🔴 | **v1.1.0** | `v1.1.0` 릴리즈 (랭그래프 에이전트 로직) |
| | 🟢 | **Fix** | Local과 Prod 환경 충돌 문제 해결, 서비스 안정장치 추가(퀴즈 횟수 제한 등) |
| **26.03.01(일)** | ⚪️ | **Add** | `AWS docker` 배포를 위한 로컬 및 aws 실행 테스트 |

## 2026년 2월 
| Date | Tag | Category | Details |
|:---:|:---:|:---:|:---|
| **26.02.27(금)** | 🟣 | **Feat** | 퀴즈 진행 과정에 시각적 효과 추가, 일부 에러 수정 |
| **26.02.26(목)** | 🟢 | **Feat** | 입력된 사용자 ID를 기반으로 퀴즈를 진행하고 저장할 수 있도록 구현 |
| **26.02.25(수)** | 🟠 | **Feat** | 스트림릿 화면 구현 및 랭스미스 서버 연결 (채팅, 키워드 시각화) |
| **26.02.24(화)** | 🟣 | **Feat** | 퀴즈 종료 후 종합 리포트 생성 로직 구현 |
| **26.02.23(월)** | 🟣 | **Feat** | 레벨별 퀴즈 출제 로직 구현, 퀴즈 진행 로직 완성도 개선 |
| **26.02.22(일)** | 🟣 | **Feat** | 퀴즈 진행 로직 에러 해결 및 다음 키워드 추천 로직 구현 |
| **26.02.19(목)** | 🟣 | **Feat** | DB 스키마 변경, 퀴즈 진행 기본 로직 구현 (질문-응답-정답-반복여부) |
| **26.02.18(수)** | 🟣 | **Feat** | 키워드 임베딩 로직 설계 |
| **26.02.16(월)** | 🟣 | **Refactor** | LangGraph 노드 독립성 개선, workflow docs 수정 |
| **26.02.15(일)** | 🟣 | **Add** | LangGraph workflow 구현 방향성 설계, evaluation node 추가 |
| **26.02.13(금)** | 🟣 | **Refactor** | LangGraph Agent 로직 단순화 (키워드 기반 문제 생성) |
| **26.02.10(화)** | 🟣 | **Refactor** | Keyword 기반 Agent 로직 초기화 (단순화) |
| **26.02.02(목)** | 🟣 | **Add** | LangGraph 로직에 tools 사용 노드 추가 |

## 2026년 1월
| Date | Tag | Category | Details |
|:---:|:---:|:---:|:---|
| **26.01.27(목)** | 🟣 | **Add** | LangGraph Template 도입(for `LangSmith`), 에이전트 로직 초안 작성|
| **26.01.22(목)** | 🔵 | **Add** | Agent_workflow 수정(버전별 구조 정리), `LangGraph` 도입 결정 |
| **26.01.21(수)** | 🔵 | **Refactor** | README.md 수정, 버전별 개발 일정 추가, 도메인 관리 규칙 추가 |
| **26.01.19(월)** | 🟠 | **Init** | `next.js` 기본 파일 생성(template 적용) 및 `Vercel` 자동 배포 |
| **26.01.18(일)** | 🟢 | **Refactor** | Ver2 개발을 위한 폴더 리팩토링 v1, v2 분리 (DB, API 등) |
| **26.01.15(목)** | 🔴 | **v1.0.0** | `v1.0.0` 릴리즈 및 kakao playmcp 등록 (심사 대기) |
| | ⚪️ | **Fix** | AWS 배포 및 playmcp 등록을 위한 https 인증서 발급 (`certbot`) |
| | ⚪️ | **Fix** | MCP server를 완전한 Stateless 구조로 변경 (mcp 등록 규정 준수) |
| **26.01.14(수)** | ⚪️ | **Add** | AWS EC2 연결(도메인 연결) 및 Docker 빌드 테스트 |
| | ⚪️ | **Add** | 서버 포트 정리 및 `Nginx` 도입 및 테스트 |
| | 🟣 | **Add** | MCP tool 코드 완성 및 테스트, Source 데이터 보강 및 동기화 |
| **26.01.13(화)** | ⚪️ | **Init** | `"haebo.pro"` 도메인 구매 |
| | 🔵 | **Feat** | mcp Tool(survey) 추가 및 mcp_schema 문서 수정 |
| | 🟣 | **Feat** | Pydantic Model 구현 (Structured Output) |
| **26.01.12(월)** | 🟣 | **Fix** | MCP-SDK 구조로 변경(playmcp 규정), tool docstring 수정 |
| | 🟢 | **Add** | Dockerfile 수정 및 테스트, Ver1 서버 빌드 및 로컬 테스트 |
| **26.01.11(일)** | 🟢 | **Add** | Langserve API 도입(for mcp), docker file 작성 |
| | 🟢 | **Feat** | Source Data를 DB로 이관, Trend 분류 도입 |
| **26.01.10(토)** | 🟢 | **Feat** | DB collection 생성 및 track 데이터 동기화 로직 구현 |
| **26.01.09(금)** | 🟢 | **Update** | db_schema.md 에 맞춰 pydantic model 코드 수정 |
| | 🔵 | **Update** | Source Data에 맞춰 db schema 구조 변경 |
| **26.01.08(목)** | 🟣 | **Add** | Trend Search 로직 분석 및 Tavily API 성능 개선 |
| **26.01.07(수)** | 🟣 | **Refactor** | MCP 코드 리팩토링 및 docstring 세부 수정 |
| **26.01.06(화)** | 🟣 | **Add** | MCP Trend Search 기능 구현 및 Streamlit 테스트 |
| **26.01.05(월)** | 🟣 | **Add** | Evaluator, QAmaker agent 로직 구현 및 연결 |
| | 🔵 | **Init** | MCP 문서 초기화 (Agent와의 기능분리) |
| **26.01.04(일)**| 🟣 | **Add** | Interviewer Agent 초기 대화 흐름 구현 / 테스트 코드 추가 |
| | 🔵 | **Update** | track.md 문서 검토 / topic Track-Tier-Level 구조 추가 |
| **26.01.03(토)** | 🟢 | **Refactor** | Stateless MCP와 Stateful api server 폴더 분리 |
| | 🔵 | **Refactor** | Agent 아키텍처(Main-sub) 및 MCP 구조 변경 문서 작성|

## 2025년 12월
| Date | Tag | Category | Details |
|:---:|:---:|:---:|:---|
| **25.12.29(일)** | 🔵 | **Update** | Agent 구현을 위한 track.md 개념 구조 정리 |
| **25.12.28(일)** | ⚪️ | **Update** | Github Project 생성, Issue & Milestone 관리 방식 정리 |
| **25.12.25(목)** | 🟣 | **Add** | 문제 생성 기본 구조 구현, 테스트 코드 추가 |
| **25.12.24(수)** | 🟣 | **Add** | AI 기본 랭체인 OpenAI 모델 연결 및 테스트 |
| | 🟢 | **Add** | DB CRUD(생성, 조회, 수정, 삭제) 유틸리티 클래스 구현, import 경로 검토 |
| **25.12.23(화)** | 🟢 | **Add** | `MongoDB Atlas` 클러스터 생성 및 스키마 작성, schema 폴더 구조 정리 |
| **25.12.22(월)** | 🟢 | **Init** | BE 기본 구조 생성, python 개발 환경 설정, `OpenAI` API Key 생성 |
|  | ⚪️ | **Init** | `AWS` 계정 생성, 깃헙 브랜치 전략 시작 |
| **25.12.21(일)** | ⚪️ | **Update** | 깃헙 레포지토리 이름 변경 (권고 규칙 적용) |
| **25.12.20(토)** | 🔵 | **Add** | mcp_server.md 문서 작성 (for `MCP-player-10`) |
| | 🔵 | **Update** | Roadmap 수정 (MCP 도입 반영) |
| **25.12.17(수)** | 🔵 | **Update** | tech_decisions.md 문서 검토 및 수정 |
| **25.12.15(월)** | 🔵 | **Update** | AI Agent workflow 검토 및 수정 |
| **25.12.13(토)** | 🔵 | **Update** | Sprint Roadmap 구체화, troubleshooting & references 문서 작성 |
| **25.12.12(금)** | 🔵 | **Add** | Architecture & Tech Decisions 문서 작성, Git-flow & Roadmap 수립 |
| **25.12.10(수)** | 🔵 | **Add** | agent_workflow.md, db_schema.md 문서 작성 |
| **25.12.08(월)** | 🔵 | **Add** | User Flow(Flowchart) 작성, Main README 개선 |
| **25.12.06(토)** | 🔵 | **Init** | 기본 구조 생성, Personas, Product Spec 작성 |
| **25.12.03(수)** | 🔵 | **Init** | 통합 레포지토리 및 파트별(FE/BE/Docs) 구조 생성 |
| **25.12.02(화)** | 🔵 | **Init** | 대략적 과정 및 내용 정리, README 기본 내용 작성 |
| **25.12.01(월)** | 🔴 | **Init** | `AI-TechTree` 프로젝트 시작, 목표 설정 | 