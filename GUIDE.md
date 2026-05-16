# TechTree 실행 및 배포 가이드

> TechTree는 **Next.js frontend + FastAPI backend + OpenAI Realtime + LangGraph evaluator** 기반의 AI 모의면접 서비스입니다.
> 로컬 개발은 직접 실행을 기본으로 하고, 운영 배포는 AWS EC2에서 **Docker Compose + Nginx + Certbot**으로 진행합니다.

---

## 0. AWS 인스턴스 설정값

운영 배포 기준 인스턴스는 아래 설정을 권장합니다.

| 항목 | 설정값 |
| :--- | :--- |
| Region | `Asia Pacific (Seoul) ap-northeast-2` |
| Instance type | `t3.small` |
| vCPU / Memory | `2 vCPU / 2 GiB RAM` |
| AMI | `Ubuntu Server 24.04 LTS` 또는 `22.04 LTS` |
| Architecture | `x86_64` |
| Storage | `gp3 30 GiB` |
| Public IP | Enabled |
| Elastic IP | 권장 |
| Domain | `techtree.haebo.pro` -> EC2 Elastic IP |
| Security Group | `22`, `80`, `443` 허용 |
| SSH Source | 내 IP만 허용 |
| HTTP/HTTPS Source | `0.0.0.0/0`, `::/0` |
| Swap | `2 GiB` |

보안 그룹 운영 원칙:

- 외부에는 `80`, `443`만 서비스 포트로 공개합니다.
- `22`는 내 IP에서만 접근하도록 제한합니다.
- `3000` Next.js, `8000` FastAPI는 Docker 내부 네트워크에서만 접근하고 외부에 직접 열지 않습니다.

---

## 1. 환경 변수

백엔드는 `backend/.env`, `backend/.env.local` 파일을 사용합니다.

### 로컬 개발

로컬 전용 값은 `backend/.env.local`에 둡니다.

```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
MONGODB_URL=your_mongodb_url
RESEND_API_KEY=your_resend_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
INVITE_SESSION_SECRET=your_long_random_secret
APP_ENV=LOCAL
```

### AWS 운영 배포

운영 서버에서는 `backend/.env`를 사용합니다.

```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
MONGODB_URL=your_mongodb_url
RESEND_API_KEY=your_resend_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
INVITE_SESSION_SECRET=your_long_random_secret
APP_ENV=PRODUCTION
```

주의:

- `.env`, `.env.local` 파일은 Git에 커밋하지 않습니다.
- `docker compose config`는 `env_file` 값을 펼쳐 출력할 수 있으므로, 결과를 공유할 때 API 키가 노출되지 않게 주의합니다.

---

## 2. 로컬 개발 환경

로컬에서는 Docker 없이 backend와 frontend를 각각 실행하는 방식을 기본으로 합니다.

### Backend 실행

```bash
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --port 8000
```

확인:

```text
http://localhost:8000/docs
```

### Frontend 실행

```bash
cd frontend
npm install
npm run dev
```

확인:

```text
http://localhost:3000
http://localhost:3000/debug
```

현재 frontend는 `/api/*` 요청을 Next.js rewrite를 통해 `http://localhost:8000/api/*`로 전달합니다.

### 로컬 검증 명령

```bash
.venv/bin/python -m compileall backend/app
```

```bash
cd frontend
npm run lint
npm run build
```

---

## 3. 로컬 Docker 검증

Docker 기반 로컬 smoke test가 필요하면 `docker-compose.local.yml`을 사용합니다.

```bash
docker compose -f docker-compose.local.yml build backend frontend
docker compose -f docker-compose.local.yml up -d backend frontend nginx
```

확인:

```bash
curl -I http://localhost:8080
curl -I http://localhost:8080/api/docs
docker compose -f docker-compose.local.yml logs -f
```

종료:

```bash
docker compose -f docker-compose.local.yml down
```

로컬 Docker 구성:

- `frontend`: Next.js standalone, 내부 `3000`
- `backend`: FastAPI/uvicorn, 내부 `8000`
- `nginx`: 로컬 reverse proxy, 외부 `8080`

---

## 4. AWS 서버 초기 세팅

### EC2 접속

```bash
ssh -i /path/to/aws_techtree.pem ubuntu@<EC2_PUBLIC_IP>
ssh techtree-server # alias 설정 후 사용
```

### 패키지 업데이트

```bash
sudo apt update
sudo apt upgrade -y
```

### Swap 2GiB 설정

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

### Docker 설치

```bash
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker ubuntu
```

그룹 권한 반영을 위해 SSH를 다시 접속합니다.

```bash
exit
ssh -i /path/to/aws_techtree.pem ubuntu@<EC2_PUBLIC_IP>
docker version
docker compose version
```

---

## 5. AWS Docker 배포

운영 배포는 EC2에서 repository를 `git clone` 또는 `git pull` 한 뒤, 서버에서 Docker Compose로 이미지를 빌드하고 실행하는 방식을 기본으로 합니다. 단, secret은 Git에 포함하지 않고 `backend/.env`만 서버에서 직접 작성하거나 로컬에서 전송합니다.

### 5.1 서버에서 repository 준비

최초 배포:

```bash
cd ~
git clone <REPOSITORY_URL> ai-techtree-project
cd ~/ai-techtree-project
```

이미 clone되어 있다면:

```bash
cd ~/ai-techtree-project
git pull
```

### 5.2 운영 환경 변수 준비

운영 서버에서는 `backend/.env`를 사용합니다. VS Code/SCP로 전송하거나 서버에서 직접 작성합니다.

서버에서 직접 작성:

```bash
cd ~/ai-techtree-project
nano backend/.env
```

로컬에서 전송:

```bash
ssh techtree-server "mkdir -p ~/ai-techtree-project/backend"
scp backend/.env techtree-server:~/ai-techtree-project/backend/.env
```

필수:

- `OPENAI_API_KEY`

선택 기능별:

- `TAVILY_API_KEY`
- `MONGODB_URL`
- `RESEND_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

초대코드 인증 관련:

- `INVITE_AUTH_ENABLED`: 기본값 `true`. `false`로 두면 초대코드 인증을 우회합니다.
- `INVITE_DB_NAME`: 초대코드 저장 DB. 없으면 `DB_NAME`을 사용합니다.
- `INVITE_COLLECTION_NAME`: 기본값 `invite_codes`.
- `INVITE_SESSION_SECRET`: 초대 인증 세션 서명용 secret. 운영에서는 반드시 별도 난수 값을 둡니다.
- `INVITE_SESSION_COOKIE_NAME`: 기본값 `techtree_invite_session`.

초대코드 문서 구조:

```json
{
  "code": "TECHTREE-ABCDEFG",
  "name": "",
  "status": "active",
  "use_max": 1,
  "use_count": 0
}
```

`status=active`이고 `use_count < use_max`인 경우에만 입장할 수 있습니다. 기본 생성 코드는 `use_max=1`인 1회용 코드입니다.

### 5.3 DNS 연결

Route 53 또는 DNS 관리 페이지에서 아래 레코드를 설정합니다.

```text
techtree.haebo.pro A <EC2_ELASTIC_IP>
```

DNS 전파 확인:

```bash
dig techtree.haebo.pro
```

### 5.4 최초 HTTP 부팅

SSL 인증서가 아직 없으면 HTTPS Nginx 설정이 바로 뜰 수 없습니다. 먼저 bootstrap 설정으로 HTTP만 올립니다.

```bash
cd ~/ai-techtree-project
docker compose -f docker-compose.yml -f docker-compose.bootstrap.yml up -d --build backend frontend nginx
```

확인:

```bash
curl -I http://techtree.haebo.pro
curl -I http://techtree.haebo.pro/api/docs
```

### 5.5 SSL 인증서 발급

```bash
docker compose run --rm certbot certonly \
  --webroot \
  -w /var/www/certbot \
  -d techtree.haebo.pro \
  --email YOUR_EMAIL@example.com \
  --agree-tos \
  --no-eff-email
```

인증서 발급 후 운영 설정으로 재기동합니다.

```bash
docker compose down
docker compose up -d --build
```

운영 `docker-compose.yml`의 `certbot` 컨테이너는 12시간마다 `certbot renew`를 실행합니다. `nginx` 컨테이너는 갱신된 인증서를 다시 읽을 수 있도록 6시간마다 `nginx -s reload`를 수행합니다. 갱신 직후 즉시 반영이 필요하면 아래 명령으로 수동 리로드할 수 있습니다.

```bash
docker compose exec nginx nginx -s reload
```

확인:

```bash
curl -I https://techtree.haebo.pro
curl -I https://techtree.haebo.pro/api/docs
```

---

## 6. 운영 명령

컨테이너 상태:

```bash
docker compose ps
```

로그 확인:

```bash
docker compose logs -f nginx
docker compose logs -f frontend
docker compose logs -f backend
```

재배포:

```bash
cd ~/ai-techtree-project
git pull
docker compose up -d --build --remove-orphans
```

중지:

```bash
docker compose down
```

인증서 갱신 테스트:

```bash
docker compose run --rm certbot renew --dry-run
docker compose exec nginx nginx -s reload
```

---

## 7. 초대코드 및 알림 운영

초대코드 인증은 스크래핑/무단 API 호출을 줄이기 위한 최소 접근 제어입니다. 사용자는 메인 화면에서 초대코드를 입력해야 하며, 인증 성공 후에만 이력서 분석, 공고 분석, 면접 시작 API를 호출할 수 있습니다.

기본 50개 1회용 코드 생성:

```bash
.venv/bin/python backend/scripts/create_invite_code.py
```

관리용 이름을 공통으로 넣어 50개 생성:

```bash
.venv/bin/python backend/scripts/create_invite_code.py --name haebo
```

특정 코드 1개 생성 또는 덮어쓰기:

```bash
.venv/bin/python backend/scripts/create_invite_code.py --code TECHTREE-ABCDEFG --name haebo
```

생성 규칙:

- 자동 생성 코드는 `TECHTREE-{무작위 문자숫자열 7자리}` 형식입니다.
- 혼동을 줄이기 위해 `0`, `O`, `1`, `I`는 자동 생성 문자에서 제외합니다.
- `--use-max`를 지정하지 않으면 `1`로 저장되어 1회용으로 동작합니다.

텔레그램 알림:

- 인증 성공 시 `code`, `name`, `status`, `usage`가 텔레그램으로 전송됩니다.
- 백엔드 `ERROR`/`CRITICAL` 로그도 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`가 있으면 텔레그램으로 전송됩니다.
- 알림 전송 실패는 사용자 인증 성공 흐름을 막지 않습니다.

주의:

- 현재 인증 세션은 HttpOnly browser session cookie입니다. 같은 브라우저의 다른 탭에서도 공유되며, 브라우저 세션이 끝날 때 만료됩니다.
- 초대코드를 완전히 비활성화하려면 MongoDB 문서의 `status`를 `disabled`로 변경합니다.

---

## 8. 서비스 사용 흐름

운영 접속:

```text
https://techtree.haebo.pro
```

주요 페이지:

- `/`: 지원자 정보, 이력서, 채용 공고, 면접 모드 입력
- `/interview`: OpenAI Realtime WebRTC 음성 면접
- `/complete`: 면접 종료 및 이메일 리포트 안내
- `/debug`: 개발자용 Realtime/debug 페이지

면접 사용 시 주의:

- 브라우저 마이크 권한을 허용해야 합니다.
- 답변할 때는 `Space`를 누른 채 말하고, 답변이 끝나면 손을 뗍니다.
- 리포트는 면접 종료 후 백그라운드에서 생성되어 이메일로 발송됩니다.

---

## 9. 문제 해결

### Next.js dev lock 오류

```text
Unable to acquire lock at frontend/.next/dev/lock
```

해결:

```bash
rm -rf frontend/.next
cd frontend
npm run dev
```

### Turbopack corrupted database 오류

```text
Failed to restore task data (corrupted database or bug)
```

해결:

```bash
rm -rf frontend/.next
cd frontend
npm run build
```

### Docker build가 메모리 부족으로 실패

운영 EC2에서 Docker 이미지를 빌드하므로, t3.small에서는 swap 설정을 먼저 확인합니다.

```bash
free -h
```

swap이 없다면 [AWS 서버 초기 세팅](#4-aws-서버-초기-세팅)의 swap 설정을 적용합니다.

### HTTPS 인증서가 없어서 Nginx가 시작하지 않음

처음 배포할 때는 bootstrap compose를 사용합니다.

```bash
docker compose -f docker-compose.yml -f docker-compose.bootstrap.yml up -d --build backend frontend nginx
```

이후 Certbot으로 인증서를 발급한 뒤 기본 compose로 재기동합니다.
