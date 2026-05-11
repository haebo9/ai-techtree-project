# TechTree MVP 및 개발 계획

## 1. 서비스 개요

TechTree는 지원자의 기본 정보, 이력서, 채용 공고, 면접 대화를 바탕으로 실시간 AI 면접을 진행하고 최종 평가 리포트와 관련 채용 공고를 제공하는 가상 면접 서비스입니다.

- 대상: 취업 준비생, 이직 준비자, 직무 전환 준비자
- 목표: 실제 면접에 가까운 음성 면접, 개인화 질문, 직무 적합성 피드백, 관련 채용 공고 연결
- 현재 단계: MVP 이후 기능 고도화 및 면접 에이전트 자기 개선 로직 실험

---

## 2. 단계별 기능 진화

### 2.1 초기 MVP

목표는 "기본 정보 입력 → AI 면접 진행 → 평가 리포트 확인"까지의 최소 흐름을 완성하는 것이었습니다.

- 기본 정보 입력: 지원 직무, 경력, 학력, 이력 요약
- 실시간 면접: OpenAI Realtime + WebRTC 기반 음성 면접
- 답변 방식: Space 기반 Push-To-Talk
- 면접 진행: 기본 면접관 프롬프트, 꼬리 질문, LangGraph 대화 상태 관리
- 최종 리포트: 점수, 강점, 개선점, 주요 Q&A 피드백

초기 MVP에는 다음 기능이 포함되지 않았습니다.

- 공고/이력서 분석
- Tavily 채용 검색
- 추천 공고 표시
- 이메일 전송
- 자동 종료 감지
- Reflexion 기반 자기 개선

### 2.2 이후 추가된 기능

1. 맞춤형 면접 입력 확장
   - PDF/TXT 이력서 텍스트 추출
   - 채용 공고 텍스트/이미지 분석
   - 공고에서 직무명 자동 추출

2. 실제 채용 공고 추천
   - Tavily 기반 채용 공고 검색
   - JobKorea/Saramin/Wanted/Jumpit/Incruit 상세 공고 URL 선별
   - 검색 결과 목록 페이지, 마감 공고, 직무 불일치 공고 제거

3. 지원자 조건 반영
   - 경력/학력 정보를 검색 쿼리에 반영
   - 신입 지원자에게 5년차 이상 공고가 노출되는 문제 완화
   - 면접 시작 전 선별한 공고를 면접 컨텍스트와 최종 리포트에 재사용

4. 면접 UX 안정화
   - 빠른 연습 7분, 실전 연습 20분 내외 면접 흐름 가이드
   - 자기소개와 지원 동기 질문을 초반에 자연스럽게 배치
   - 직접 입력한 지원 직무를 다시 묻지 않도록 프롬프트 개선
   - 종료 멘트 감지 후 리포트 자동 생성
   - Realtime voice별 면접관 이름 매칭

5. 에이전트 자기 개선
   - 면접 종료 후 비식별 reflection 저장
   - 유사 조건 면접에 보정 지침 주입
   - 반복 인사이트를 candidate policy로 집계
   - 검증된 지침을 promoted policy로 승격
   - 더 나은 지침이 생기면 기존 정책을 deprecated 처리

---

## 3. 현재 구현 구조

### 3.1 Frontend

- 기본 정보 입력 화면
- 면접 진행 화면
- 최종 리포트 화면
- 이메일 전송 UI
- 디버그 페이지

### 3.2 Backend API

- `/api/interview/start`: Realtime 세션 생성, 시스템 프롬프트 구성, LangGraph 상태 초기화
- `/api/interview/tools/search_job`: Realtime tool call에서 Tavily 채용 검색 실행
- `/api/interview/{session_id}/end`: transcript 평가, 리포트 생성, 비식별 reflection 저장
- `/api/interview/{session_id}/email`: 리포트 이메일 전송
- `/api/upload/*`: 이력서/채용 공고 텍스트 추출 및 직무명 추출

### 3.3 Interview Agent

- 기본 시스템 프롬프트는 면접 흐름과 방법만 담당
- 지원 직무가 입력되어 있으면 확정 정보로 사용
- 공고가 없을 때도 입력 직무 기준으로 질문과 채용 검색 수행
- 빠른 연습 7분, 실전 연습 20분 내외를 목표로 질문 수와 마무리 시점 조정
- 목소리별 면접관 이름을 시스템 프롬프트에 주입

### 3.4 Job Search

- Tavily API로 실시간 채용 공고 검색
- 상세 공고 URL만 우선 선별
- 마감/종료/지난 공고 필터링
- 검색 결과 목록 페이지 제거
- 직무 관련성 필터링
- 경력/학력 조건 기반 검색 및 후처리

### 3.5 Evaluation & Report

- LangGraph evaluator가 transcript를 분석
- 점수, 강점, 개선점, 주요 Q&A 피드백 생성
- 면접 중 수집된 `saved_jobs`를 최종 리포트 추천 공고로 사용
- 추천 공고는 면접 시작 전 선별된 모집중 공고만 사용
- Resend API로 이메일 리포트 발송

---

## 4. 맞춤형 면접 입력

이력서와 채용 공고 분석은 단순 업로드 편의 기능이 아니라, 사용자 맞춤 면접을 위한 핵심 입력입니다.

### 4.1 이력서

- 지원자의 프로젝트, 경험, 기술 스택을 추출
- 개인화된 질문과 꼬리 질문의 근거로 사용
- 답변 검증 시 이력 내용과 실제 설명의 일관성을 확인

### 4.2 채용 공고

- 실제 공고의 직무, 필수 요건, 우대조건을 면접 기준으로 사용
- 공고가 있으면 해당 포지션에 맞춘 질문을 우선 생성
- 공고가 없으면 입력된 지원 직무와 Tavily 검색 결과를 기준으로 대체

### 4.3 경력/학력

- 질문 난이도 조정에 사용
- 채용 공고 검색 조건에 반영
- 신입/주니어/경력직에 맞지 않는 질문과 공고 추천을 줄이는 데 사용

---

## 5. 에이전트 자기 개선 로직

현재 자기 개선은 모델 파라미터를 학습시키는 방식이 아닙니다. 면접 경험에서 얻은 운영 지침을 MongoDB/로컬 저장소에 누적하고, 다음 면접 프롬프트에 동적으로 주입하는 비모수 메모리 방식입니다.

### 5.1 저장소

- MongoDB `reflection` database
  - `interview_reflections`: 개별 면접에서 생성된 비식별 운영 지침 저장
  - `interview_policies`: 반복 근거가 쌓인 운영 정책과 상태 관리
  - `embedding_text`, `embedding`, `embedding_model` 필드로 Atlas Vector Search 준비
  - 읽기는 MongoDB/vector search를 우선 사용
  - 저장은 MongoDB와 JSONL에 모두 수행하고, DB 연결 실패 시 JSONL만 유지
  - `backend/scripts/setup_reflection_db.py`로 컬렉션/인덱스 생성을 점검

- `backend/app/source/interview_reflections.jsonl`
  - 로컬 백업/fallback용 비식별 운영 지침 저장
  - 전체 대화 원문, 이력서 원문, 채용 공고 원문은 저장하지 않음

- `backend/app/source/interview_policies.jsonl`
  - 로컬 백업/fallback용 운영 지침 관리
  - `candidate`, `promoted`, `deprecated` 상태를 가짐

### 5.2 Policy 상태

- `candidate`
  - 비식별 reflection이 집계되어 정책 후보가 된 상태
  - 아직 근거가 부족하므로 기본 프롬프트에는 주입하지 않음

- `promoted`
  - 여러 면접에서 반복 근거와 confidence가 쌓여 공식 운영 정책으로 승격된 상태
  - 다음 유사 면접에 우선 주입

- `deprecated`
  - 더 좋은 정책에 대체되었거나 중복/충돌/효과 부족으로 더 이상 쓰지 않는 상태
  - 프롬프트에 주입하지 않음

### 5.3 동작 흐름

1. 면접 종료 후 transcript, 평가 결과, 추천 공고를 기반으로 비식별 reflection 생성
   - transcript는 요청 처리와 reflection 생성에만 사용하고 별도 저장하지 않음
   - 저장되는 값은 `issue`, `lesson`, `prompt_hint` 형태의 짧은 운영 지침으로 제한
2. 동일 직무/경력/학력 조건에서 유사 지침이 반복되면 candidate policy로 집계
3. evidence count와 confidence 기준을 넘으면 promoted policy로 승격
4. 더 구체적이거나 근거가 강한 정책이 생기면 기존 정책은 deprecated로 강등
5. 다음 면접 시작 시 promoted policy를 먼저 주입
6. 최근 유사 reflection은 보조 지침으로 제한 주입
7. MongoDB vector index가 준비된 환경에서는 직무/경력/학력 기반 semantic search로 유사 지침을 검색
   - 검색 쿼리에는 저장하지 않는 이력 요약/공고 컨텍스트/면접 모드를 짧은 힌트로만 사용

### 5.4 설계 원칙

- 기본 시스템 프롬프트는 전체 면접 흐름과 방법만 설명
- 누적 경험에 따른 세부 개선은 동적 지침으로 반영
- 모델 개선은 원문 데이터셋 축적이 아니라 비식별 운영 지침의 누적과 승격/강등으로 수행
- 평가 점수 자체보다 면접관 행동 품질, 실패 재발 여부, 질문 관련성을 더 중요하게 봄
- 벡터 DB도 transcript 원문이 아니라 `prompt_hint`, `lesson`, `policy`만 벡터화
- 검색 시에는 새 면접의 직무, 경력, 학력, 이력 요약, 공고 힌트를 사용하되 해당 입력 원문은 저장하지 않음

---

## 6. 품질 관리

- backend compile 검사
- job search 필터 테스트
- reflection/policy 승격 테스트
- prompt 회귀 테스트
- 전체 backend 테스트 기준: `39 passed`

현재 남은 경고:

- 현재 알려진 주요 Pydantic deprecation warning은 `ConfigDict` 전환으로 정리됨

---

## 7. MVP 제외 및 아직 미구현

- 사용자 계정/로그인
- 면접 기록 영구 저장 및 사용자별 히스토리
- 리포트 PDF 다운로드
- 관리자 대시보드
- 채용 공고 즐겨찾기/지원 관리
- 다중 면접 비교 분석
- 장기 성장 그래프
- 실제 지원서 제출 연동

---

## 8. 향후 구현 과제

### 8.1 면접 품질 평가 루프

- policy 준수율 측정
- 실패 재발 여부 확인
- 질문 관련성 평가
- 평가 가능한 대화가 충분한지 요청 처리 중 판단하되, 원문은 저장하지 않음

### 8.2 면접 에이전트 자율성 조정

- 답변 품질에 따른 난이도 조정
- 꼬리 질문 횟수와 주제 전환 판단
- 평가 전 정보 충분성 판단
- 7분/20분 모드별 시간 운영 정교화

### 8.3 채용 검색 고도화

- 사이트별 상세 페이지 파싱
- 마감일, 경력, 학력, 우대조건 구조화
- 추천 공고별 추천 이유 제공

### 8.4 입력 정보 확장

- 전공 정보 선택 입력 추가
- 검색에는 약한 힌트로 사용
- 면접 질문 개인화에 반영

### 8.5 Reflexion 저장소 고도화

- Atlas Vector Search index를 운영 DB에 생성
- vector similarity 점수와 policy evidence/confidence를 함께 반영한 ranking 고도화
- 관리자 화면에서 candidate/promoted/deprecated 상태 점검

### 8.6 리포트 개선

- PDF 다운로드
- 질문별 점수
- 공고 적합도
- 답변 개선 예시

---

## 9. 배포 계획

### 9.1 Docker

- 과거 Streamlit 기준 Docker 설정을 Next.js + FastAPI 기준으로 재정리
- backend Docker image와 frontend 배포 방식 분리
- local/prod compose 파일 분리
- `OPENAI_API_KEY`, `TAVILY_API_KEY`, `RESEND_API_KEY` 등 secret 주입 방식 정리
- `/api`와 frontend 라우팅을 Nginx에서 명확히 분리

### 9.2 AWS

- 초기 배포는 EC2 기반 운영으로 시작
- FastAPI backend는 EC2에서 Docker Compose로 실행
- HTTPS는 Nginx + Certbot 사용
- frontend는 Vercel 또는 EC2 내 Next.js standalone 중 선택
- 최소 모니터링: health check, API error log, Realtime session error log

---

## 10. 다음 마일스톤

1. policy 효과 평가용 evaluator 추가
2. Promoted Policy 자동 승격/강등 기준 보수화
3. 채용 공고 요건/우대조건 구조화
4. Docker 배포 구조 정리
5. AWS 테스트 배포
