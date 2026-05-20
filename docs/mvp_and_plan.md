# TechTree MVP 및 개발 계획

## 1. 서비스 개요

TechTree는 이력서, 채용 공고, 지원 직무, 경력, 학력 정보를 바탕으로 실제 대화처럼 진행되는 AI 음성 모의면접 서비스입니다. 사용자는 면접관과 실시간으로 말하고, 면접이 끝나면 대화 내역을 기반으로 점수, 강점, 개선점, 상세 Q&A 피드백, 말투/자기소개/직무 적합도 분석이 담긴 이메일 리포트를 받습니다.

- 대상: 면접을 반복 연습하고 싶은 지원자
- 핵심 가치: 실제 면접에 가까운 음성 경험, 개인화 질문, 대화 기반 피드백, 반복 연습을 통한 개선
- 현재 단계: MVP 이후 배포 안정화 및 Reflection/Policy 기반 면접관 자기개선 고도화

포트폴리오 관점에서 TechTree는 “AI를 실제 사용자 경험으로 연결한다”는 방향성을 서비스로 검증한 프로젝트입니다. 실시간 음성 UX, LangGraph 기반 평가, 비식별 Reflection/Policy 메모리, Docker/AWS 운영 구성을 하나의 서비스 사이클로 연결했습니다.

## 2. MVP에서 현재 버전까지의 진화

### 초기 MVP

초기 목표는 “기본 정보 입력 → AI 면접 진행 → 평가 리포트 확인”까지 이어지는 최소 흐름 완성이었습니다.

- 지원 직무, 경력, 학력, 이력 요약 입력
- OpenAI Realtime + WebRTC 기반 음성 면접
- Space 기반 Push-to-Talk 답변
- LangGraph 기반 평가 워크플로우
- 점수, 강점, 개선점, Q&A 피드백 생성

### 현재 추가된 기능

- 초대코드 인증
  - MongoDB Atlas `reflection.invite_codes` 컬렉션 기반 접근 제어
  - HttpOnly session cookie 발급
  - 인증 성공 및 서버 오류 Telegram 알림

- 맞춤형 입력 분석
  - PDF 이력서 텍스트 추출
  - TXT/직접 입력 지원
  - 채용 공고 텍스트/이미지 분석
  - 공고에서 직무명 자동 추출

- 면접 UX
  - 빠른 연습과 실전 연습 모드
  - WebRTC 직접 연결 기반 저지연 음성 면접
  - VAD 대신 Push-to-Talk로 답변 시작/종료를 사용자가 제어
  - 면접관 마무리 흐름과 종료 버튼 기반 종료
  - 첫 면접관 음성 전 준비 오버레이

- 평가와 이메일 리포트
  - 면접 종료 후 FastAPI background task로 리포트 생성
  - Resend 기반 이메일 발송
  - 전체 대화 내역 포함
  - 점수, 강점, 개선점, 상세 Q&A, 말투/답변 습관, 자기소개 개선안, 이력서-직무 적합도 제공

- 자기개선 루프
  - 면접 종료 후 원문이 아닌 비식별 reflection 생성
  - 유사 면접 조건에 운영 지침 주입
  - 반복 근거가 쌓인 지침을 policy 후보로 집계
  - promoted/deprecated 상태로 지침 품질 관리

- 배포
  - Next.js standalone frontend
  - FastAPI backend
  - Docker Compose
  - Nginx reverse proxy
  - Certbot HTTPS
  - AWS EC2 운영 흐름

## 3. 현재 구현 구조

### Frontend

- `/`: 초대코드 인증, 입력 폼, 서비스 소개 페이지
- `/interview`: OpenAI Realtime WebRTC 면접 화면
- `/complete`: 면접 종료 후 리포트 생성/이메일 발송 안내
- `/result`: legacy/manual report view
- `/debug`: 프롬프트와 Realtime 입출력 확인용 개발자 도구

### Backend API

- `GET /api/invite/session`: 초대코드 인증 세션 확인
- `POST /api/invite/verify`: 초대코드 검증 및 session cookie 발급
- `POST /api/upload/parse-pdf`: PDF 이력서 텍스트 추출
- `POST /api/upload/analyze-jd`: 채용 공고 텍스트/이미지 분석 및 직무명 추출
- `POST /api/interview/start`: 면접 컨텍스트 준비 및 OpenAI Realtime client secret 발급
- `POST /api/interview/{session_id}/end`: 면접 종료, 리포트 생성 background task 등록
- `POST /api/interview/{session_id}/email`: 세션 리포트 이메일 발송 보조 API

### AI Workflow

- `interview_manager`가 입력값, 공고 분석, 면접 모드, reflection/policy 지침을 조합합니다.
- OpenAI Realtime 시스템 프롬프트는 면접관 행동, 질문 흐름, 종료 방식, 모드별 운영 기준을 정의합니다.
- 브라우저는 client secret으로 OpenAI Realtime에 직접 WebRTC 연결합니다.
- 면접 종료 후 LangGraph evaluator가 transcript를 구조화 평가합니다.
- ReflectionService는 평가 결과와 대화 흐름에서 다음 면접에 재사용할 운영 지침을 생성합니다.

## 4. 데이터와 개인정보 원칙

- 이력서와 채용 공고 원문은 장기 저장하지 않습니다.
- 면접 종료 후 이메일 리포트와 reflection 생성에 필요한 처리에만 transcript를 사용합니다.
- 저장되는 자기개선 데이터는 `prompt_hint`, `lesson`, `policy` 같은 비식별 운영 지침입니다.
- 초대코드는 MongoDB Atlas `reflection.invite_codes`를 사용하고, reflection/policy는 MongoDB를 우선 사용하되 JSONL fallback을 가집니다.
- 브라우저에는 같은 정보로 다시 연습하기를 위해 `sessionStorage`가 사용될 수 있습니다.

## 5. Reflection/Policy 자기개선 계획

현재 자기개선은 모델 파라미터를 학습시키는 방식이 아닙니다. 면접 경험에서 얻은 운영 지침을 저장하고, 다음 유사 면접의 시스템 프롬프트에 일부 주입하는 비모수 메모리 방식입니다.

동작 흐름:

1. 면접 종료 후 evaluator가 평가 리포트를 생성합니다.
2. Reflection analyzer가 원문 저장 없이 비식별 운영 지침을 생성합니다.
3. 지침은 직무, 경력, 학력, 면접 모드 범위와 함께 저장됩니다.
4. 다음 면접 시작 시 유사 조건의 promoted policy와 reflection 일부가 선택됩니다.
5. 선택된 지침만 프롬프트에 주입됩니다.
6. 지침이 반복적으로 효과를 보이면 positive outcome이 쌓이고, 실패가 반복되면 negative outcome이 쌓입니다.
7. 근거와 confidence가 충분하면 policy로 승격되고, 더 나은 policy가 생기면 기존 policy는 deprecated 처리됩니다.

설계 원칙:

- 원문 데이터 축적보다 운영 지침의 품질을 관리합니다.
- 모든 reflection을 매번 주입하지 않고 조건과 limit에 맞는 일부만 사용합니다.
- short/long 모드와 맞지 않는 지침은 제외합니다.
- promoted policy가 reflection보다 우선됩니다.

## 6. 배포 계획

최종 배포 기준은 AWS EC2에서 repository를 clone/pull하고 서버에서 Docker Compose로 빌드하는 방식입니다.

운영 구성:

- Squarespace DNS: `techtree.haebo.pro` A 레코드를 EC2 Elastic IP에 연결
- AWS EC2 Elastic IP/Security Group: AWS Console에서 설정
- `backend/Dockerfile`: Python 3.12 FastAPI backend
- `frontend/Dockerfile`: Node 22 Next.js standalone frontend
- `docker-compose.yml`: 운영 컨테이너 구성
- `nginx/default.conf`: HTTPS reverse proxy
- `docker-compose.bootstrap.yml`: 최초 인증서 발급 전 HTTP bootstrap
- `certbot`: Let's Encrypt 인증서 발급/갱신

초기 배포 순서:

1. AWS Console에서 EC2, Security Group, Elastic IP를 준비합니다.
2. Squarespace DNS에서 `techtree` A 레코드를 Elastic IP로 연결합니다.
3. EC2에서 repository를 clone/pull하고 `backend/.env`를 작성합니다.
4. `docker-compose.bootstrap.yml`로 HTTP 서비스를 먼저 올립니다.
5. Certbot `certonly`로 최초 인증서를 발급합니다.
6. 기본 `docker-compose.yml`로 HTTPS 운영 서비스를 재기동합니다.

일반 재배포 명령:

```bash
git pull
docker compose up -d --build --remove-orphans
```

## 7. 향후 과제

- `/complete`에서 리포트 생성 상태를 조회하는 API/UI 추가
- in-memory `temp_sessions`를 Redis/Mongo 등 영속 저장소로 전환
- Reflection/Policy 관리용 운영 도구 추가
- 리포트 PDF 다운로드 또는 공유용 보기 추가
- 면접 모드별 시간 운영과 종료 판단 정교화
- Debug page에서 Realtime event와 transcript 정합성 검증 강화
- 이메일 템플릿의 브랜드 테마 통일
- 테스트 커버리지와 배포 smoke test 문서화
