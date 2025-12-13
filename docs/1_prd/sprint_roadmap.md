# 📅 Project Roadmap: AI TechTree
> **Timeline**: 2025.12.01 ~ 2026.05.31 (Total 6 Months)  
> **Strategy**: **MVP First (선 배포 후 개선)** 전략 - 2월 말 핵심 기능 런칭 후 기술 고도화

---

## 📝 Phase 0: Planning & Design 
`2025.12 초 ~ 2025.12 중순`
> **Goal**: 서비스의 방향성 정의 및 핵심 문서화 완료

- [x] **Sprint 0 (12월 1주~2주): 기획 및 기술 조사**
    - [x] 서비스 컨셉 구체화 (AI TechTree, Skill Sync)
    - [x] 핵심 기능 정의 (User Flow, PRD 작성)
    - [x] 기술 스택 선정 및 아키텍처 설계
    - [x] 개발 문서 템플릿 및 규칙(Convention) 수립

## 🏗 Phase 1: Foundation & Walking Skeleton 
`2025.12 말 ~ 2026.01 초`
> **Goal**: "안녕"이라고 치면 화면에 뜨는, **배포된** 빈 껍데기(Skeleton) 완성

- [ ] **Sprint 1 (12월 3주~4주): 환경 구축 및 CI/CD**
    - [ ] Monorepo (Next.js + FastAPI) Scaffolding
    - [ ] **[중요]** CI/CD 파이프라인 구축 (GitHub Actions)
    - [ ] **[중요]** Hello World 배포 (Vercel + AWS EC2) → *배포 환경 선제 구축*

- [ ] **Sprint 2 (1월 1주~2주): E2E 통신 연결**
    - [ ] UI: 채팅 인터페이스 기본 레이아웃 (Shadcn/ui)
    - [ ] Server: FastAPI 기본 엔드포인트 생성 및 CORS 설정
    - [ ] DB: MongoDB Atlas 클러스터 생성 및 연결 테스트

## ⚡ Phase 2: MVP Development 
`2026.01 중순 ~ 2026.02 말`
> **Goal**: 실제 동작하는 에이전트와 시각화 기능 구현 (**v1.0.0 배포**)

- [ ] **Sprint 3 (1월 3주~4주): 기본 에이전트 & 스트리밍**
    - [ ] AI: OpenAI API 연동 (LangGraph 도입 전, 단순 호출로 구현)
    - [ ] Backend: SSE(Server-Sent Events) 스트리밍 구현
    - [ ] Frontend: 실시간 답변 렌더링 처리

- [ ] **Sprint 4 (2월 1주~2주): 시각화 & 데이터 저장**
    - [ ] Frontend: React Flow 설치 및 스킬 트리 시각화 구현
    - [ ] Backend: 대화 내역(History) 및 사용자 데이터 DB 저장 로직
    - [ ] AI: 면접관 페르소나 프롬프트 튜닝

- [ ] **Sprint 5 (2월 3주~4주): MVP 통합 및 런칭**
    - [ ] 기능 통합: 채팅-시각화 상호작용 연동
    - [ ] **🚀 v1.0.0 MVP Launch**: 서비스 배포 및 주변 지인 피드백 수집

## 🔧 Phase 3: Iteration & Deep Dive 
`2026.03 ~ 2025.03`
> **Goal**: **LangGraph** 도입 및 기술적 챌린지 해결

- [ ] **Sprint 6 (3월 1주~2주): AI 로직 고도화 (LangGraph)**
    - [ ] **[Refactoring]** 단순 API 로직을 **LangGraph State Machine**으로 전환
    - [ ] 순환 참조 및 복잡한 대화 흐름(질문-평가-재질문) 제어
    - [ ] 에이전트 모듈화 (Interviewer / Evaluator 분리)

- [ ] **Sprint 7 (3월 3주~4주): 성능 개선 및 UX 고도화**
    - [ ] 최적화: 응답 속도 개선 (Redis 캐싱 도입 등)
    - [ ] UX: MVP 피드백 반영 (UI 디테일 수정, 모바일 최적화)
    - [ ] 예외 처리: API 에러 핸들링 및 재시도 로직 강화

## 💎 Phase 4: Polish & Stabilization 
`2026.04 ~ 2026.05`
> **Goal**: 코드 품질 향상 및 서비스 안정화

- [ ] **Sprint 8 (4월 1주~2주): 안정성 확보**
    - [ ] Test: Pytest(Backend) / Jest(Frontend) 단위 및 통합 테스트 작성
    - [ ] Refactoring: 코드 구조 개선, 불필요한 의존성 제거

- [ ] **Sprint 9 (4월 3주~4주): 문서화 및 회고**
    - [ ] 기술 블로그: 트러블 슈팅 및 기술 도입 배경 정리
    - [ ] README.md 업데이트: 아키텍처 다이어그램, 시연 GIF 추가
