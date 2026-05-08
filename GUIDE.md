# 🚀 Techtree AI 면접관 실행 가이드

> 이 프로젝트는 **FastAPI(Backend)** 와 **Next.js(Frontend)** 로 구성되어 있습니다. 실시간 음성 면접을 시작하려면 아래 단계를 따라주세요.

---

## 1. 필수 환경 변수 설정
각 디렉토리의 `.env` 파일에 API 키가 설정되어 있어야 합니다.

### **Backend (`/backend/.env`)**
```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
```

---

## 2. 서버 실행 방법

### **Step 1: Backend 서버 실행**
백엔드는 Python 기반입니다. 새 터미널을 열고 아래 명령어를 입력하세요.
```bash
source .venv/bin/activate  # (선택사항) 가상환경 활성화
cd backend
uvicorn app.main:app --reload --port 8000
```
> 서버가 성공적으로 실행되면 `http://localhost:8000/docs`에서 API 문서를 확인할 수 있습니다.

### **Step 2: Frontend 앱 실행**
또 다른 새 터미널을 열고 아래 명령어를 입력하세요.
```bash
cd frontend
npm run dev
```
> 브라우저에서 `http://localhost:3000`으로 접속하면 메인 화면이 뜹니다.

---

## 3. 주요 페이지 정보
*   **메인 페이지**: `http://localhost:3000` (지원자 정보 입력)
*   **면접 페이지**: 메인 페이지에서 시작 버튼 클릭 시 이동
*   **개발자 디버그 페이지**: `http://localhost:3000/debug` (실시간 로그 및 툴 동작 확인 가능)

---

## ⚠️ 주의사항
*   **Push-To-Talk**: 답변할 때는 **스페이스바를 누른 채**로 말씀하시고, 답변이 끝나면 손을 떼셔야 AI가 인식을 시작합니다.
*   **마이크 권한**: 브라우저에서 마이크 사용 권한 요청 시 반드시 '허용'을 눌러주세요.
*   **API 에러 (422)**: 만약 토큰 발급 시 422 에러가 발생한다면 메인 페이지에서 다시 정보를 입력하고 접속하시거나 브라우저 캐시를 삭제해 주세요.
