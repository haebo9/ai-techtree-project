# TechTree Frontend

TechTree frontend는 Next.js App Router 기반의 AI 모의면접 UI입니다. 초대코드 인증, 지원자 정보 입력, 이력서/채용 공고 업로드, OpenAI Realtime WebRTC 면접 화면, 완료 안내 화면, 개발자 디버그 화면을 담당합니다.

## Local Development

```bash
npm install
npm run dev
```

기본 접속 주소:

```text
http://localhost:3000
```

로컬 개발에서는 `next.config.ts`의 rewrite가 `/api/*` 요청을 기본적으로 `http://localhost:8000/api/*`로 전달합니다. 다른 백엔드를 사용하려면 `BACKEND_INTERNAL_URL`을 설정합니다.

## Key Pages

- `/`: 초대코드 인증, 면접 정보 입력, 서비스 소개
- `/interview`: OpenAI Realtime WebRTC 음성 면접
- `/complete`: 비동기 이메일 리포트 생성 안내
- `/result`: legacy/manual report view
- `/debug`: Realtime 세션과 transcript 확인용 개발자 도구

## Checks

```bash
npm run lint
npm run build
```
