# TechTree Documentation

TechTree 문서는 최종 배포, 개발자 온보딩, 포트폴리오 설명을 함께 지원하기 위해 관리됩니다.

## 핵심 문서

- [TechTree Wiki](./techtree-wiki.md): 서비스 목적, 전체 아키텍처, API 흐름, Realtime 면접, 평가, Reflection/Policy 자기개선, Docker/AWS 배포를 한 번에 설명하는 기준 문서
- [User Flow](./user_flow.md): 사용자가 보는 화면 흐름과 시스템 내부 처리 순서
- [MVP and Plan](./mvp_and_plan.md): MVP에서 현재 배포 버전까지의 기능 진화와 향후 과제

## 설계와 의사결정

- [Architecture](./architecture.md): 시스템 아키텍처 초안과 구조 설계 기록
- [Agent Workflow](./agent_workflow.md): AI 에이전트 워크플로우 설계 기록
- [Tech Decisions](./tech_decisions.md): 주요 기술 선택과 의사결정 배경
- [References](./references.md): 공식 문서, 디자인 레퍼런스, 폰트와 색상 기준

## 운영 보조 문서

- [Deployment Guide](../GUIDE.md): 로컬 실행, Docker Compose, AWS EC2, Nginx, Certbot 배포 절차
- [Project Structure](../STRUCTURE.md): 현재 저장소 구조와 주요 파일 역할
- [Development Log](./dev_log.md): 개발 진행 기록

## 현재 기준

- 기본 제품 흐름은 `/` → `/interview` → `/complete` → 이메일 리포트입니다.
- `/result`는 legacy/manual report 화면입니다.
- 최종 리포트의 핵심은 점수, 강점, 개선점, 상세 Q&A, 말투/자기소개/직무 적합도, 전체 대화 내역입니다.
- 채용 공고 검색은 면접 컨텍스트와 도구 실행 기록을 보조하는 기능이며, 최종 리포트의 핵심 홍보 요소로 다루지 않습니다.
