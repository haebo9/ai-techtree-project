# v1.1 Deployment Guide (AWS EC2)

이 가이드는 현재 작성된 `docker-compose.yml` 및 로컬 설정들을 기반으로, **v1.1 버전 백엔드를 안전하게 수동 배포하기 위한 가이드**입니다.

모든 명령어는 루트 디렉토리 `ai-techtree-project` 에서 실행한다고 가정합니다.

---

### Step 1. 새로운 백엔드 이미지 빌드 및 푸시

로컬 환경에서 최신 v1.1 이미지를 빌드하여 Docker Hub(또는 ECR)에 업로드합니다.

```bash
# 1. 태그를 v1.1로 지정하여 플랫폼에 맞게 빌드
docker build --no-cache --platform linux/amd64 -t haebo/ai-techtree:v1.1 .

# 2. 빌드된 이미지를 원격 저장소에 Push
docker push haebo/ai-techtree:v1.1
```

> **Tip:** Docker 로그인(`docker login`)이 되어있는지 미리 확인하세요.

---

### Step 2. 로컬에서 도커 컨테이너 빌드 및 테스트해보기 (선택사항)

서버에 배포하기 전에 방금 만든 이미지가 내 컴퓨터(로컬)에서 똑같이 잘 동작하는지 미리 테스트해 볼 수 있습니다.

```bash
# 로컬 전용 설정 파일(docker-compose.local.yml)을 사용하여 백그라운드 실행
docker-compose -f docker-compose.local.yml up -d

# 정상적으로 모든 컨테이너가 떴는지(Up 상태) 확인
docker-compose -f docker-compose.local.yml ps

# 로그를 보면서 오류가 없는지 확인
docker-compose -f docker-compose.local.yml logs -f

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

업데이트된 `docker-compose.yml` 파일과 최신 `.env` 파일을 서버 홈 디렉토리(`~/`)로 복사합니다.

```bash
# SSH 접속 정보(techtree-server)는 ~/.ssh/config 에 설정된 이름을 기준으로 합니다.
scp docker-compose.yml .env techtree-server:~
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

### ✅ 프로덕션(AWS) 배포 성공 후 접속 URL 정보
Nginx 설정과 도메인이 정상적으로 연결되었다면, 기본적으로 80(HTTP), 443(HTTPS) 포트로 자동 포워딩됩니다. 
현재 설정(`docker-compose.yml` 및 `nginx/default.conf` 구조 등)을 기반으로 한 예상 주소입니다:

* **프론트엔드 (Streamlit UI)**: 연결해둔 메인 도메인 (예: `https://haebo.pro` 또는 `http://3.38.85.58`)
* **백엔드 (FastAPI Swagger)**: `https://haebo.pro/api/docs` (또는 `http://3.38.85.58/api/docs`)
* **에이전트 (LangGraph Server)**: 외부에는 `/threads/` 엔드포인트 등을 통해 HTTPS 기반(`https://haebo.pro/threads/...`)으로 내부 API 포트(2024)에 접근하게 됩니다. 

에러가 발생하지 않아야 배포가 정상적으로 완료된 것입니다. 수고하셨습니다.
