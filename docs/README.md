# TechTree Documentation

TechTree 문서는 최종 배포, 개발자 온보딩, 포트폴리오 설명을 함께 지원하기 위해 관리됩니다. 처음 코드를 확인하는 사람은 아래 순서대로 읽으면 제품 목적, 실행 방법, 내부 구조, 운영 절차를 자연스럽게 파악할 수 있습니다.

## 추천 읽기 순서

1. [README](../README.md): 서비스 소개, 핵심 기능, 기술 스택, 빠른 실행 안내.
2. [Service Screens](./service_screens.md): 실제 화면 흐름을 이미지로 빠르게 확인.
3. [User Flow](./user_flow.md): 사용자의 화면 이동과 시스템 내부 처리 순서 확인.
4. [TechTree Wiki](./techtree-wiki.md): 제품 목적부터 Realtime, 평가, Reflection/Policy, 배포까지 한 번에 정리한 기준 문서.
5. [Deployment Guide](../GUIDE.md): 로컬 실행, Docker smoke test, AWS EC2/Nginx/Certbot 배포 절차.
6. [Project Structure](../STRUCTURE.md): 현재 저장소 구조와 주요 파일 역할.
7. [Tech Decisions](./tech_decisions.md): 주요 기술 선택 이유와 운영 원칙.

## 문서 목록

| 구분 | 문서 | 역할 |
| :--- | :--- | :--- |
| 서비스 이해 | [Service Screens](./service_screens.md) | 홈, 면접, 완료, 리포트, 디버그 화면을 이미지로 확인합니다. |
| 서비스 이해 | [User Flow](./user_flow.md) | 초대코드부터 이메일 리포트까지 사용자 흐름과 API 흐름을 함께 설명합니다. |
| 기준 문서 | [TechTree Wiki](./techtree-wiki.md) | 제품 목적, 전체 아키텍처, Realtime 면접, 평가, 자기개선, 배포 구조를 종합합니다. |
| 계획 | [MVP and Plan](./mvp_and_plan.md) | MVP에서 현재 배포 버전까지의 기능 진화와 향후 과제를 정리합니다. |
| 설계 | [Architecture](./architecture.md) | 버전별 시스템 아키텍처 변화와 현재 배포 경계를 설명합니다. |
| 설계 | [Agent Workflow](./agent_workflow.md) | v1.0부터 v2.0까지 AI 에이전트 워크플로우의 진화를 정리합니다. |
| 의사결정 | [Tech Decisions](./tech_decisions.md) | Next.js, FastAPI, WebRTC, LangGraph, MongoDB, Docker 배포 선택 이유를 설명합니다. |
| 참고 | [References](./references.md) | 공식 문서, 디자인 레퍼런스, 폰트와 색상 기준을 모읍니다. |
| 운영 | [Deployment Guide](../GUIDE.md) | 로컬 실행, Docker Compose, AWS EC2, Nginx, Certbot 배포 절차입니다. |
| 운영 | [Project Structure](../STRUCTURE.md) | 현재 저장소 구조와 주요 파일 역할입니다. |
| 기록 | [Development Log](./dev_log.md) | 주요 개발 진행 기록입니다. |

## 현재 기준

- 기본 제품 흐름은 `/` → `/interview` → `/complete` → 이메일 리포트입니다.
- `/result`는 legacy/manual report 화면입니다.
- 최종 리포트의 핵심은 점수, 강점, 개선점, 상세 Q&A, 말투/자기소개/직무 적합도, 전체 대화 내역입니다.
- 채용 공고 검색은 면접 컨텍스트와 도구 실행 기록을 보조하는 기능이며, 최종 리포트의 핵심 홍보 요소로 다루지 않습니다.
- 포트폴리오 설명에서는 1인 개발로 기획, AI 워크플로우, WebRTC 음성 UX, 백엔드 API, Docker/AWS 배포까지 연결한 실서비스형 프로젝트라는 점을 중심에 둡니다.
