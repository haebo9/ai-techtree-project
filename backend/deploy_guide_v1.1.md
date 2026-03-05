# v1.1 Deployment Guide (AWS EC2)

이 가이드는 현재 작성된 `docker-compose.yml` 및 로컬 설정들을 기반으로, **v1.1 버전 백엔드를 안전하게 수동 배포하기 위한 가이드**입니다.

모든 명령어는 루트 디렉토리 `ai-techtree-project` 에서 실행한다고 가정합니다.

---

### Step 1. 도커 이미지 빌드하기 (환경에 따라 선택)

**A. 클라우드 서버(AWS EC2) 등 실 배포용으로 빌드할 때** (작업 환경이 Mac인 경우 필수)
로컬(Mac) 환경에서 Linux용 이미지를 빌드하여 원격 저장소에 올립니다.
```bash
# 1. 태그를 v1.1로 지정하여 리눅스 플랫폼에 맞게 빌드
docker build --no-cache --platform linux/amd64 -t haebo/ai-techtree:v1.1 .

# 2. 빌드된 이미지를 원격 저장소(Docker Hub/ECR)에 Push
docker push haebo/ai-techtree:v1.1
```

**B. 나와 동일한 로컬 환경(로컬 컴퓨터)에서 직접 띄워볼 때** (팀원용 / 로컬 테스트용)
플랫폼 지정 없이 현재 컴퓨터 환경에 맞게 이미지를 빌드합니다.
```bash
docker build -t ai-techtree:local-v1.1 .

# 이 이미지는 Step 2에서 직접 사용하거나 로컬 컨테이너 디버깅용으로 쓸 수 있습니다.
```

> **Tip:** Docker 로그인(`docker login`)이 되어있는지 미리 확인하세요.

---

### Step 2. 로컬에서 도커 컨테이너 실행 및 테스트 (선택사항)
도커 없이 단순히 서버를 띄워 테스트 할수 있습니다. 
```bash
# LangGraph 서버 
cd backend
langgraph dev

# fastapi 서버
cd backend
uvicorn app.main:app --reload

# frontend next.js 서버
cd frontend
npm run dev
```

서버에 배포하기 전에 방금 만든 이미지가 로컬 환경에서 미리 테스트해 볼 수 있습니다.

```bash
# .env 파일 생성 필수! (MONGODB_URL, OPENAI_API_KEY 등 세팅)
# 로컬 전용 설정 파일(docker-compose.local.yml)을 사용하여 빌드 및 백그라운드 실행
docker-compose -f docker-compose.local.yml up -d --build

# 정상적으로 모든 컨테이너가 떴는지(Up 상태) 확인
docker-compose -f docker-compose.local.yml ps

# 로그를 보면서 오류가 없는지 확인
docker-compose -f docker-compose.local.yml logs -f

# 컨테이너 재시작(선택 사항)
docker-compose -f docker-compose.local.yml restart

# 테스트가 끝났다면 컨테이너 종료 및 삭제
docker-compose -f docker-compose.local.yml down
```

### ✅ 로컬 접속 URL 정보
도커가 성공적으로 띄워진 경우 아래 주소로 접속하여 테스트할 수 있습니다.
* **프론트엔드 (Streamlit UI)**: `http://localhost:8100`
* **백엔드 (FastAPI Swagger)**: `http://localhost:8000/docs`
* **에이전트 (LangGraph Server)**: `http://localhost:2024`

> **Tip:** 로컬에서 Nginx 포트(80, 443) 충돌이 날 수 있으므로, 방화벽이나 80포트를 따로 띄우지 않은 경우 위처럼 직접 포트 번호(8100 등)로 접속해서 확인하세요.

---

### Step 3. 서버로 설정 파일 전송 (SCP)

업데이트된 `docker-compose.yml` 파일과 최신 `backend/.env` 파일을 서버 홈 디렉토리(`~/`)로 복사합니다.

```bash
# SSH 접속 정보(techtree-server)는 ~/.ssh/config 에 설정된 이름을 기준으로 합니다.
# 1. 서버 상의 backend 디렉토리 생성 (필요한 경우)
ssh techtree-server "mkdir -p backend"

# 2. docker-compose.yml 및 .env 파일 전송 
# (docker-compose.yml에 지정된 ./backend/.env 경로와 일치해야 함)
scp docker-compose.yml techtree-server:~/
scp backend/.env techtree-server:~/backend/
```

> **Note:** Nginx 설정이 변경되었다면 `scp -r nginx techtree-server:~/` 명령어도 추가로 실행해주세요.

---

### Step 4. 서버에 접속하여 배포 실행

서버에 SSH로 접속한 뒤, 변경된 파일을 반영하고 컨테이너를 재시작합니다.

```bash
# 1. EC2 서버에 SSH 접속
ssh techtree-server

# ---------- 서버 내부에서 실행 ----------

# 2. docker-compose.yml 내의 이미지 태그 확인
# 현재 로컬에서 수정된 yml 파일이 전송되었지만, 만약 파일 내 백엔드/프론트엔드/mcp 이미지 태그가
# 여전히 'haebo/ai-techtree:v1' 로 되어 있다면 'v1.1' 로 수정해주셔야 합니다.
# (nano docker-compose.yml 등을 통해 확인 요망)

# 3. 최신 이미지 풀링 및 컨테이너 재시작
docker-compose pull
docker-compose down
docker-compose up -d --remove-orphans

# 4. 백엔드 로그 확인 (정상적으로 띄워지는지 상태 점검)
docker-compose logs -f backend
```

---

### Step 5. 무료 SSL 인증서(HTTPS) 발급받기 (최초 1회 필수)
신규 도메인(`techtree.haebo.pro`)에 대한 HTTPS 접속을 활성화하려면, 첫 배포 시 반드시 아래 명령어를 실행하여 Let's Encrypt 인증서를 발급해야 Nginx 컨테이너가 정상적으로 구동됩니다.

```bash
# 1. Certbot 컨테이너를 이용해 인증서 발급 (이메일 및 도메인 입력 필요)
docker-compose run --rm certbot certonly --webroot --webroot-path=/var/www/certbot -d techtree.haebo.pro

# 발급 과정:
# - 이메일 주소 입력 (로그 및 만료 알림용)
# - 약관 동의 (A 누르고 Enter)
# - 이메일 정보 공유 (Y 또는 N 누르고 Enter)

# 2. 발급 완료 후 Nginx 컨테이너 재시작 (인증서 반영)
docker-compose restart nginx
```

---

### ✅ 프로덕션(AWS) 배포 성공 후 접속 URL 정보
Nginx 설정과 도메인이 정상적으로 연결되었다면, 기본적으로 80(HTTP), 443(HTTPS) 포트로 자동 포워딩됩니다. 
현재 설정(`docker-compose.yml` 및 `nginx/default.conf` 구조 등)을 기반으로 한 예상 주소입니다:

* **프론트엔드 (Streamlit UI)**: 연결해둔 메인 도메인 (예: `https://techtree.haebo.pro` 또는 `http://3.38.85.58`)
* **백엔드 (FastAPI Swagger)**: `https://techtree.haebo.pro/api/docs` (또는 `http://3.38.85.58/api/docs`)
* **에이전트 (LangGraph Server)**: 외부에는 `/threads/` 엔드포인트 등을 통해 HTTPS 기반(`https://techtree.haebo.pro/threads/...`)으로 내부 API 포트(2024)에 접근하게 됩니다. 

에러가 발생하지 않아야 배포가 정상적으로 완료된 것입니다. 수고하셨습니다.
