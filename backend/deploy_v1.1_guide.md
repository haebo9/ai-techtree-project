# v1.1 Deployment Guide (AWS EC2)

이 가이드는 현재 작성된 `docker-compose.yml` 및 로컬 설정들을 기반으로, **v1.1 버전 백엔드를 안전하게 수동 배포하기 위한 가이드**입니다.

모든 명령어는 루트 디렉토리 `/Users/seo/Documents/develop/ai-techtree-project` 에서 실행한다고 가정합니다.

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

### Step 2. 서버로 설정 파일 전송 (SCP)

업데이트된 `docker-compose.yml` 파일과 최신 `.env` 파일을 서버 홈 디렉토리(`~/`)로 복사합니다.

```bash
# SSH 접속 정보(techtree-server)는 ~/.ssh/config 에 설정된 이름을 기준으로 합니다.
scp docker-compose.yml .env techtree-server:~/
```

> **Note:** Nginx 설정이 변경되었다면 `scp -r nginx techtree-server:~/` 명령어도 추가로 실행해주세요.

---

### Step 3. 서버에 접속하여 배포 실행

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

에러가 발생하지 않아야 배포가 정상적으로 완료된 것입니다. 수고하셨습니다.
