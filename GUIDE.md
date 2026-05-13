# TechTree 실행 및 배포 가이드

> TechTree는 **Next.js frontend + FastAPI backend + OpenAI Realtime + LangGraph evaluator** 기반의 AI 모의면접 서비스입니다.
> 로컬 개발은 직접 실행을 기본으로 하고, 운영 배포는 AWS EC2에서 **Docker Compose + Nginx + Certbot**으로 진행합니다.

---

## Index

1. [AWS 인스턴스 설정값](#0-aws-인스턴스-설정값)
2. [환경 변수](#1-환경-변수)
3. [로컬 개발 환경](#2-로컬-개발-환경)
4. [로컬 Docker 검증](#3-로컬-docker-검증)
5. [AWS 서버 초기 세팅](#4-aws-서버-초기-세팅)
6. [AWS Docker 배포](#5-aws-docker-배포)
7. [운영 명령](#6-운영-명령)
8. [서비스 사용 흐름](#7-서비스-사용-흐름)
9. [문제 해결](#8-문제-해결)

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
| SSH Source | 가능하면 내 IP만 허용 |
| HTTP/HTTPS Source | `0.0.0.0/0`, `::/0` |
| Swap | `2 GiB` 권장 |

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

### 5.1 코드 업로드

Git을 사용한다면:

```bash
git clone <REPOSITORY_URL> ai-techtree-project
cd ai-techtree-project
```

또는 로컬에서 서버로 전송합니다.

```bash
rsync -av --exclude .git --exclude .venv --exclude frontend/node_modules --exclude frontend/.next ./ ubuntu@<EC2_PUBLIC_IP>:~/ai-techtree-project
```

### 5.2 운영 환경 변수 준비

서버에서 `backend/.env`를 작성합니다.

```bash
cd ~/ai-techtree-project
nano backend/.env
```

필수:

- `OPENAI_API_KEY`

선택 기능별:

- `TAVILY_API_KEY`
- `MONGODB_URL`
- `RESEND_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

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
git pull
docker compose up -d --build
```

중지:

```bash
docker compose down
```

인증서 갱신 테스트:

```bash
docker compose run --rm certbot renew --dry-run
```

---

## 7. 서비스 사용 흐름

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

## 8. 문제 해결

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

t3.small에서는 swap 설정을 먼저 확인합니다.

```bash
free -h
```

swap이 없다면 [AWS 서버 초기 세팅](#4-aws-서버-초기-세팅)의 swap 설정을 적용합니다.

### HTTPS 인증서가 없어서 Nginx가 시작하지 않음

처음 배포할 때는 bootstrap compose를 사용합니다.

```bash
docker compose -f docker-compose.yml -f docker-compose.bootstrap.yml up -d backend frontend nginx
```

이후 Certbot으로 인증서를 발급한 뒤 기본 compose로 재기동합니다.
