# TechTree 실행 및 배포 가이드

> TechTree는 **Next.js frontend + FastAPI backend + OpenAI Realtime WebRTC + LangGraph evaluator** 기반의 AI 모의면접 서비스입니다.
> 이 문서는 처음 코드를 받은 사람이 로컬에서 서비스를 실행하고, 필요하면 Docker smoke test와 AWS 운영 배포까지 순서대로 진행할 수 있도록 작성되었습니다.

---

## 0. 전체 진행 순서

> 처음 코드를 받은 사람은 로컬 실행을 먼저 성공시키고, 그다음 Docker와 AWS 배포로 확장하는 순서로 진행합니다.

처음 세팅한다면 아래 순서대로 진행합니다.

1. [필수 도구와 환경 변수 준비](#1-필수-도구와-환경-변수-준비)
2. [로컬에서 backend 실행](#2-로컬에서-backend-실행)
3. [로컬에서 frontend 실행](#3-로컬에서-frontend-실행)
4. [서비스 동작 확인](#4-서비스-동작-확인)
5. [로컬 검증 명령 실행](#5-로컬-검증-명령-실행)
6. [선택: 로컬 Docker smoke test](#6-선택-로컬-docker-smoke-test)
7. [선택: AWS EC2 운영 배포](#7-선택-aws-ec2-운영-배포)
8. [초대코드 및 운영 보조 기능](#8-초대코드-및-운영-보조-기능)
9. [문제 해결](#9-문제-해결)

로컬 개발 기본 주소:

- Frontend: `http://localhost:3000`
- Debug page: `http://localhost:3000/debug`
- Backend docs: `http://localhost:8000/docs`

운영 배포 기본 주소:

- Service: `https://techtree.haebo.pro`
- API docs: `https://techtree.haebo.pro/api/docs`

외부 웹 콘솔에서 직접 설정하는 항목:

- 도메인 구매 및 DNS 관리: Squarespace에서 `haebo.pro` 도메인을 구매하고 DNS 레코드를 설정합니다.
- (저의 도메인을 예시로 들어 문서를 작성하였지만 실제로 구현을 할 떄는 자신만의 도메인을 선택 및 사용하면 됩니다.)
- 고정 퍼블릭 IP: AWS Console에서 EC2 Elastic IP를 생성하고 인스턴스에 연결합니다.

위 두 항목은 서버 터미널에서 설정하는 것이 아니라, 각 서비스의 웹 UI에서 직접 설정합니다.

---

## 1. 필수 도구와 환경 변수 준비

> backend가 먼저 정상 기동되어야 frontend와 면접 흐름을 확인할 수 있습니다. 이 단계에서는 Python/Node 의존성과 API key를 준비합니다.

### 1.1 필수 도구

로컬 직접 실행에는 아래 도구가 필요합니다.

| 항목 | 권장 버전 | 용도 |
| :--- | :--- | :--- |
| Python | `3.12.13` | FastAPI backend, LangGraph evaluator |
| Node.js | `22.x` | Next.js frontend |
| npm | Node.js 포함 | frontend dependency 설치 및 빌드 |

Docker smoke test 또는 AWS 배포까지 진행하려면 Docker Compose도 필요합니다.

### 1.2 Python 의존성

이미 `.venv`가 준비되어 있다면 활성화해서 사용합니다.

```bash
source .venv/bin/activate
```

새로 만드는 경우:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 1.3 Backend 환경 변수

백엔드는 아래 파일을 순서대로 읽습니다.

```text
backend/.env
.env
backend/.env.local
.env.local
```

로컬 개발에서는 `backend/.env.local`을 권장합니다.

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

필수:

- `OPENAI_API_KEY`: Realtime session 발급과 LLM 평가에 필요합니다.

선택 기능별:

- `TAVILY_API_KEY`: 실제 채용 공고 검색
- `MONGODB_URL`: 초대코드, Reflection/Policy Mongo 저장소
- `RESEND_API_KEY`: 이메일 리포트 발송
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: 운영 로그/초대코드 인증 알림

초대코드 인증 관련:

- `INVITE_AUTH_ENABLED`: 기본값 `true`. `false`로 두면 초대코드 인증을 우회합니다.
- `INVITE_DB_NAME`: 초대코드 저장 DB. 운영 권장값은 `reflection`입니다.
- `INVITE_COLLECTION_NAME`: 기본값 `invite_codes`.
- `INVITE_SESSION_SECRET`: 초대 인증 세션 서명용 secret. 운영에서는 반드시 별도 난수 값을 둡니다.
- `INVITE_SESSION_COOKIE_NAME`: 기본값 `techtree_invite_session`.

주의:

- `.env`, `.env.local` 파일은 Git에 커밋하지 않습니다.
- `docker compose config`는 `env_file` 값을 펼쳐 출력할 수 있으므로, 결과를 공유할 때 API 키가 노출되지 않게 주의합니다.

---

## 2. 로컬에서 Backend 실행

> FastAPI backend는 Realtime session 발급, 업로드 분석, 평가 리포트 생성, 이메일 발송을 담당합니다.

터미널 1에서 backend를 실행합니다.

```bash
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --port 8000
```

확인:

```text
http://localhost:8000/docs
```

정상이라면 FastAPI Swagger 문서가 열립니다.

---

## 3. 로컬에서 Frontend 실행

> Next.js frontend는 사용자 입력, WebRTC 면접 화면, 완료 화면, 디버그 페이지를 제공합니다.

터미널 2에서 frontend를 실행합니다.

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

로컬 frontend는 `next.config.ts`의 rewrite를 통해 `/api/*` 요청을 기본적으로 `http://localhost:8000/api/*`로 전달합니다.

다른 backend 주소를 쓰고 싶으면 frontend 실행 환경에 `BACKEND_INTERNAL_URL`을 설정합니다.

---

## 4. 서비스 동작 확인

> 서버가 켜진 뒤에는 페이지가 열리는지, 초대코드 설정이 의도대로인지, 면접 시작과 종료 흐름이 이어지는지 확인합니다.

### 4.1 기본 페이지 확인

1. `http://localhost:3000`에 접속합니다.
2. 초대코드 인증 화면 또는 면접 정보 입력 화면이 보이는지 확인합니다.
3. `/debug` 페이지가 열리는지 확인합니다.

### 4.2 초대코드 인증

기본 설정은 `INVITE_AUTH_ENABLED=true`입니다. 인증을 켠 상태라면 MongoDB Atlas의 초대코드가 필요합니다.

빠른 로컬 UI 확인만 하고 싶다면 `backend/.env.local`에 아래 값을 둘 수 있습니다.

```env
INVITE_AUTH_ENABLED=false
```

운영 환경에서는 인증 우회를 권장하지 않습니다.

### 4.3 면접 플로우 확인

1. 리포트를 받을 이메일, 지원 직무, 경력, 최종 학력을 입력합니다.
2. 이력서는 PDF/TXT 업로드, 직접 입력, 없음 중 하나로 준비합니다.
3. 채용 공고는 텍스트 또는 이미지로 입력할 수 있습니다.
4. 면접 모드를 선택한 뒤 면접을 시작합니다.
5. 브라우저 마이크 권한을 허용합니다.
6. `/interview`에서 Space를 누른 채 답변하고, 답변이 끝나면 손을 뗍니다.
7. `면접 종료하기`를 누르면 `/complete`로 이동합니다.
8. 백엔드는 백그라운드에서 평가 리포트를 생성하고, `RESEND_API_KEY`가 있으면 이메일을 발송합니다.

주의:

- OpenAI Realtime 연결에는 `OPENAI_API_KEY`가 필요합니다.
- 이메일 발송은 `RESEND_API_KEY`가 없으면 콘솔 시뮬레이션으로 처리됩니다.
- `TAVILY_API_KEY`가 없으면 실제 채용 공고 검색은 제한됩니다.

---

## 5. 로컬 검증 명령 실행

> 코드 변경 후에는 영향 범위에 맞는 가장 작은 검증부터 실행하고, 배포 전에는 backend tests와 frontend build까지 확인합니다.

Backend syntax check:

```bash
.venv/bin/python -m compileall backend/app
```

Backend tests:

```bash
.venv/bin/python -m pytest backend/tests
```

Frontend lint:

```bash
cd frontend
npm run lint
```

Frontend production build:

```bash
cd frontend
npm run build
```

Realtime/interview 흐름을 수정했다면 서버를 켠 상태로 `/`, `/interview`, `/complete`, `/debug`를 직접 확인합니다.

---

## 6. 선택: 로컬 Docker Smoke Test

> 로컬 직접 실행이 통과한 뒤, Docker 이미지와 Nginx reverse proxy 구성이 함께 동작하는지 확인하는 단계입니다.

Docker 기반으로 로컬 reverse proxy까지 확인하고 싶으면 `docker-compose.local.yml`을 사용합니다.

### 6.1 빌드 및 실행

```bash
docker compose -f docker-compose.local.yml build backend frontend
docker compose -f docker-compose.local.yml up -d backend frontend nginx
```

### 6.2 확인

```bash
curl -I http://localhost:8080
curl -I http://localhost:8080/api/docs
docker compose -f docker-compose.local.yml logs -f
```

로컬 Docker 구성:

- `frontend`: Next.js standalone, 내부 `3000`
- `backend`: FastAPI/uvicorn, 내부 `8000`
- `nginx`: 로컬 reverse proxy, 외부 `8080`

### 6.3 종료

```bash
docker compose -f docker-compose.local.yml down
```

---

## 7. 선택: AWS EC2 운영 배포

> 운영 배포는 AWS/Squarespace 웹 UI 설정과 EC2 터미널 작업이 함께 필요합니다. Elastic IP와 DNS는 웹 UI에서, Docker 실행은 EC2 터미널에서 진행합니다.

운영 배포는 EC2에서 repository를 `git clone` 또는 `git pull` 한 뒤, 서버에서 Docker Compose로 이미지를 빌드하고 실행하는 방식을 기본으로 합니다.

### 7.1 AWS 인스턴스 권장 설정

> 이 항목들은 AWS Console에서 EC2 instance를 만들 때 선택하거나, 생성 후 네트워크 설정 화면에서 직접 조정합니다.

| 항목 | 설정값 |
| :--- | :--- |
| Region | `Asia Pacific (Seoul) ap-northeast-2` |
| Instance type | `t3.small` |
| vCPU / Memory | `2 vCPU / 2 GiB RAM` |
| AMI | `Ubuntu Server 24.04 LTS` 또는 `22.04 LTS` |
| Architecture | `x86_64` |
| Storage | `gp3 30 GiB` |
| Public IP | Enabled |
| Elastic IP | AWS Console에서 생성 후 EC2 instance에 연결 |
| Domain | Squarespace DNS에서 `techtree.haebo.pro` -> EC2 Elastic IP로 연결 |
| Security Group | `22`, `80`, `443` 허용 |
| SSH Source | 내 IP만 허용 |
| HTTP/HTTPS Source | `0.0.0.0/0`, `::/0` |
| Swap | `2 GiB` |

보안 그룹 운영 원칙:

- 외부에는 `80`, `443`만 서비스 포트로 공개합니다.
- `22`는 내 IP에서만 접근하도록 제한합니다.
- `3000` Next.js, `8000` FastAPI는 Docker 내부 네트워크에서만 접근하고 외부에 직접 열지 않습니다.

AWS Console에서 직접 설정하는 항목:

- EC2 instance 생성
- Security Group inbound rule 설정
- Elastic IP 생성 및 EC2 instance 연결

Elastic IP를 사용하는 이유:

- EC2 일반 Public IP는 instance를 stop/start 하면 바뀔 수 있습니다.
- Elastic IP는 고정 IP이므로 DNS A 레코드를 안정적으로 유지할 수 있습니다.
- Squarespace DNS의 `techtree` A 레코드는 이 Elastic IP를 바라보게 설정합니다.

### 7.2 EC2 접속

```bash
ssh -i /path/to/aws_techtree.pem ubuntu@<EC2_PUBLIC_IP>
```

alias를 설정했다면 이후부터는 아래처럼 접속할 수 있습니다.

```bash
ssh techtree-server
```

### 7.3 OS 업데이트와 swap 설정

```bash
sudo apt update
sudo apt upgrade -y
```

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

### 7.4 Docker 설치

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

### 7.5 Repository 준비

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

### 7.6 운영 환경 변수 준비

> 운영 secret은 Git에 포함하지 않습니다. EC2 서버의 `backend/.env`에 직접 작성하거나 안전한 방식으로 전송합니다.

운영 서버에서는 `backend/.env`를 사용합니다.

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

운영 예시:

```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
MONGODB_URL=your_mongodb_url
RESEND_API_KEY=your_resend_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
INVITE_SESSION_SECRET=your_long_random_secret
INVITE_DB_NAME=reflection
APP_ENV=PRODUCTION
```

### 7.7 DNS 연결

> 이 단계는 Squarespace 웹 UI에서 진행합니다. EC2 터미널에서는 설정 후 `dig`로 DNS가 올바르게 전파되었는지만 확인합니다.

`haebo.pro`는 Squarespace에서 구매한 루트 도메인입니다. `techtree.haebo.pro`는 이 루트 도메인 아래에 만든 서브도메인입니다.

이 단계는 서버 터미널에서 실행하는 작업이 아니라 **Squarespace DNS 관리 화면에서 직접 설정하는 작업**입니다.

Squarespace DNS 관리 화면에서 아래 A 레코드를 설정합니다.

```text
Type: A
Host/Name: techtree
Value/Points to: <EC2_ELASTIC_IP>
TTL: 기본값
```

DNS 전파 확인:

```bash
dig techtree.haebo.pro
```

정상이라면 `techtree.haebo.pro`가 AWS Console에서 EC2에 연결한 Elastic IP를 가리켜야 합니다.

요청 흐름:

```text
Browser
  -> techtree.haebo.pro
  -> Squarespace DNS resolves to EC2 Elastic IP
  -> EC2 Security Group allows 80/443
  -> Docker Nginx receives request
  -> frontend or /api backend
```

### 7.8 최초 HTTP 부팅

> Let's Encrypt 인증서를 발급하려면 먼저 HTTP로 도메인이 열려 있어야 합니다. HTTPS 설정은 인증서 발급 후 적용합니다.

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

### 7.9 SSL 인증서 발급

> bootstrap HTTP 확인이 끝나면 Certbot으로 인증서를 발급하고, 이후 기본 compose 설정으로 HTTPS 서비스를 올립니다.

```bash
docker compose run --rm --entrypoint certbot certbot certonly \
  --webroot \
  -w /var/www/certbot \
  -d techtree.haebo.pro \
  --email YOUR_EMAIL@example.com \
  --agree-tos \
  --no-eff-email
```

`docker-compose.yml`의 `certbot` 서비스는 운영 중 자동 갱신을 위해 기본 command가 `renew` 흐름으로 잡혀 있습니다. 그래서 최초 발급 때는 위처럼 `--entrypoint certbot`을 명시해 `certonly` 명령이 그대로 실행되도록 합니다.

성공하면 아래와 비슷한 메시지가 출력됩니다.

```text
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/techtree.haebo.pro/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/techtree.haebo.pro/privkey.pem
```

발급 확인:

```bash
sudo ls -l certbot/conf/live/techtree.haebo.pro/
```

`certbot/conf/live/...` 경로는 인증서 권한 때문에 일반 `ubuntu` 사용자로는 `Permission denied`가 날 수 있습니다. 이 경우 `sudo ls`로 확인합니다.

인증서 발급 후 운영 설정으로 재기동합니다.

```bash
docker compose down
docker compose up -d --build
```

운영 `docker-compose.yml`의 `certbot` 컨테이너는 12시간마다 `certbot renew`를 실행합니다. `nginx` 컨테이너는 갱신된 인증서를 다시 읽을 수 있도록 6시간마다 `nginx -s reload`를 수행합니다.

갱신 직후 즉시 반영이 필요하면 아래 명령으로 수동 리로드할 수 있습니다.

```bash
docker compose exec nginx nginx -s reload
```

확인:

```bash
curl -I https://techtree.haebo.pro
curl -I https://techtree.haebo.pro/api/docs
```

### 7.10 운영 명령

> 배포 후에는 컨테이너 상태, 로그, 재배포, 인증서 갱신 상태를 아래 명령으로 확인합니다.

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

## 8. 초대코드 및 운영 보조 기능

> 초대코드는 공개 접근을 제한하기 위한 최소 게이트입니다. 운영에서는 MongoDB Atlas의 invite collection과 Telegram 알림 설정을 함께 관리합니다.

초대코드 인증은 스크래핑/무단 API 호출을 줄이기 위한 최소 접근 제어입니다. 사용자는 메인 화면에서 초대코드를 입력해야 하며, 인증 성공 후에만 이력서 분석, 공고 분석, 면접 시작 API를 호출할 수 있습니다.

운영 서버는 `MONGODB_URL`로 연결된 MongoDB Atlas의 `reflection.invite_codes` 컬렉션을 조회합니다. 서버 `.env`에는 명시적으로 `INVITE_DB_NAME=reflection`을 두는 것을 권장합니다.

현재 운영 기준 초대코드 컬렉션:

```text
MongoDB Atlas
  database: reflection
  collection: invite_codes
```

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

### 8.1 초대코드 생성

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

### 8.2 Telegram 알림

- 인증 성공 시 `code`, `name`, `status`, `usage`가 Telegram으로 전송됩니다.
- 백엔드 `ERROR`/`CRITICAL` 로그도 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`가 있으면 Telegram으로 전송됩니다.
- 알림 전송 실패는 사용자 인증 성공 흐름을 막지 않습니다.

### 8.3 인증 세션 주의사항

- 현재 인증 세션은 HttpOnly browser session cookie입니다.
- 같은 브라우저의 다른 탭에서도 공유되며, 브라우저 세션이 끝날 때 만료됩니다.
- 초대코드를 완전히 비활성화하려면 MongoDB 문서의 `status`를 `disabled`로 변경합니다.

---

## 9. 문제 해결

> 아래 항목은 실제 로컬/운영 배포 중 자주 만나는 오류와 우선 확인할 지점을 정리한 것입니다.

### 9.1 Next.js dev lock 오류

```text
Unable to acquire lock at frontend/.next/dev/lock
```

해결:

```bash
rm -rf frontend/.next
cd frontend
npm run dev
```

### 9.2 Turbopack corrupted database 오류

```text
Failed to restore task data (corrupted database or bug)
```

해결:

```bash
rm -rf frontend/.next
cd frontend
npm run build
```

### 9.3 Docker build가 메모리 부족으로 실패

운영 EC2에서 Docker 이미지를 빌드하므로, `t3.small`에서는 swap 설정을 먼저 확인합니다.

```bash
free -h
```

swap이 없다면 [OS 업데이트와 swap 설정](#73-os-업데이트와-swap-설정)을 적용합니다.

### 9.4 HTTPS 인증서가 없어서 Nginx가 시작하지 않음

처음 배포할 때는 bootstrap compose를 사용합니다.

```bash
docker compose -f docker-compose.yml -f docker-compose.bootstrap.yml up -d --build backend frontend nginx
```

이후 Certbot으로 인증서를 발급한 뒤 기본 compose로 재기동합니다.

최초 인증서 발급 명령은 아래처럼 `--entrypoint certbot`을 포함해 실행합니다.

```bash
docker compose run --rm --entrypoint certbot certbot certonly \
  --webroot \
  -w /var/www/certbot \
  -d techtree.haebo.pro \
  --email YOUR_EMAIL@example.com \
  --agree-tos \
  --no-eff-email
```

만약 `No renewals were attempted.`만 출력되고 인증서가 생성되지 않았다면, `certbot` 서비스의 기본 갱신 command가 실행된 것입니다. 위 명령처럼 `--entrypoint certbot`을 명시해 다시 발급합니다.

발급 확인 시 권한 오류가 나면 아래처럼 확인합니다.

```bash
sudo ls -l certbot/conf/live/techtree.haebo.pro/
```

### 9.5 API가 401을 반환함

초대코드 인증이 켜져 있는데 session cookie가 없을 때 발생합니다.

확인할 것:

- 브라우저에서 초대코드 인증을 먼저 완료했는지
- `INVITE_AUTH_ENABLED` 값이 의도한 대로 설정되어 있는지
- MongoDB의 invite code 문서가 `status=active`이고 `use_count < use_max`인지

### 9.6 이메일이 오지 않음

확인할 것:

- `RESEND_API_KEY`가 설정되어 있는지
- 입력한 이메일 주소가 올바른지
- backend 로그에 Resend 오류가 있는지
- `RESEND_API_KEY`가 없으면 이메일은 실제 발송되지 않고 콘솔 시뮬레이션으로 처리됩니다.
