# TechTree MVP 및 개발 계획

## 개요

TechTree는 지원 직무, 이력서, 채용 공고를 바탕으로 실시간 AI 면접을 진행하고 최종 리포트와 관련 채용 공고를 제공하는 가상 면접 서비스입니다.

- 대상: 취업 준비생, 이직 준비자, 직무 전환 준비자
- 목표: 실제 면접에 가까운 음성 면접 경험과 개인화 피드백 제공
- 현재 단계: MVP 기능 구현 및 안정화

---

## MVP 범위

MVP는 "기본 정보 입력 → AI 면접 진행 → 평가 리포트 확인"까지의 최소 완성 흐름입니다.

| 영역 | MVP 기능 |
| --- | --- |
| 기본 정보 | 지원 직무, 경력, 학력, 이력서, 선택적 채용 공고 입력 |
| 공고/이력서 분석 | PDF/TXT 이력서 텍스트 추출, 공고 텍스트/이미지 분석, 직무명 자동 추출 |
| 실시간 면접 | OpenAI Realtime + WebRTC 기반 음성 면접, Push-To-Talk 답변, 꼬리 질문 |
| 채용 검색 | Tavily 기반 실제 채용 공고 검색, 마감/목록/직무 불일치 공고 필터링 |
| 최종 리포트 | 점수, 강점, 개선점, Q&A 피드백, 추천 공고, 이메일 전송 |

---

## 구현 완료

| 구분 | 완료 내용 |
| --- | --- |
| Frontend | Next.js 입력 화면, 면접 화면, 결과 리포트, 이메일 전송 UI, 디버그 페이지 |
| Upload | 이력서 PDF/TXT 파싱, 채용 공고 텍스트/이미지 기반 직무 추출 |
| Interview | OpenAI Realtime 세션 생성, WebRTC 음성 연결, Space 기반 Push-To-Talk |
| Agent | 면접관 프롬프트, Realtime tool calling, LangGraph 평가 workflow |
| Job Search | Tavily 검색, 상세 공고 URL 필터, 마감 공고 필터, 경력/학력 조건 반영 |
| Report | transcript 기반 평가, `saved_jobs` 기반 실제 공고 추천, Resend 이메일 발송 |
| Quality | backend compile, 검색 필터 테스트, frontend lint/build, import chain 점검 |

---

## MVP 제외

- 사용자 계정/로그인
- 면접 기록 영구 저장
- 리포트 PDF 다운로드
- 관리자 대시보드
- 채용 공고 즐겨찾기/지원 관리
- 다중 면접 비교 분석
- 장기 성장 그래프
- 실제 지원서 제출 연동

---

## 향후 구현 과제

| 우선순위 | 과제 | 핵심 내용 |
| --- | --- | --- |
| 1 | MVP 안정화 | 면접 시작/진행/종료/리포트 흐름 오류 제거, Realtime tool 예외 처리 |
| 2 | 면접 에이전트 자율성 조정 | 답변 품질에 따른 난이도/꼬리 질문/주제 전환 조정, 평가 전 정보 충분성 판단 |
| 3 | 전공 정보 활용 | 선택 입력으로 추가, 검색에는 약한 힌트로 사용, 면접 질문 개인화에 반영 |
| 4 | 채용 검색 고도화 | 사이트별 상세 페이지 파싱, 마감일/경력/학력 요건 구조화, 추천 이유 제공 |
| 5 | 리포트 개선 | PDF 다운로드, 질문별 점수, 공고 적합도, 답변 개선 예시 |
| 6 | 배포 준비 | Docker 구조 최신화, 환경 변수/secret 관리, health check, Nginx 라우팅 정리 |
| 7 | AWS 배포 | EC2 + Docker Compose + Nginx/Certbot, 로그/모니터링, 도메인/CORS 정리 |

---

## 배포 계획

### Docker

- 현재 Docker 설정은 과거 Streamlit 구조가 일부 남아 있어 Next.js + FastAPI 기준으로 재정리 필요
- backend Docker image와 frontend 배포 방식을 분리
- local/prod compose 파일 분리
- `OPENAI_API_KEY`, `TAVILY_API_KEY`, `RESEND_API_KEY` 등 secret 주입 방식 정리
- `/api`와 frontend 라우팅을 Nginx에서 명확히 분리

### AWS

- 초기 배포는 단순한 EC2 기반 운영으로 시작
- FastAPI backend는 EC2에서 Docker Compose로 실행
- HTTPS는 Nginx + Certbot 사용
- frontend는 Vercel 배포 또는 EC2 내 Next.js standalone 배포 중 선택
- 최소 모니터링: health check, API error log, Realtime session error log

---

## 다음 마일스톤

1. 면접 에이전트 자율성 조정 로직 설계
2. 채용 공고 검색 결과의 요건/우대조건 구조화
3. Docker 배포 구조 정리
4. AWS 테스트 배포
