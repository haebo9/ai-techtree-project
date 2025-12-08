# User Flow (서비스 흐름도)

## 📌 개요
사용자가 서비스에 진입하여 자신의 Tech Tree를 완성해나가는 전체적인 흐름을 정의합니다.
핵심 흐름은 **온보딩(초기 배치)**, **성장(승급 심사)**, **완성(트랙 마스터)** 세 단계로 구분됩니다.

## 1. Flowchart Overview (Mermaid)

```mermaid
graph TD
    %% Nodes
    Start((Start)) --> Landing[랜딩 페이지]
    Landing --> Login[로그인/회원가입]
    
    Login --> HasAccount{계정 존재?}
    HasAccount -->|No| InitTest[📝 초기 역량 배치고사]
    HasAccount -->|Yes| Dashboard[🌳 Tech Tree 대시보드]
    
    InitTest -->|결과 분석| SetBaseStats[기본 1차 전직 부여]
    SetBaseStats --> Dashboard
    
    Dashboard --> ClickNode[노드/기술 선택]
    ClickNode --> CheckStatus{상태 확인}
    
    CheckStatus -->|Locked| Disabled["진입 불가 (선행 학습 필요)"]
    CheckStatus -->|Available| SelectLevel["도전 등급 선택 (2차/3차)"]
    CheckStatus -->|Mastered| Review[복습 하기]
    
    SelectLevel --> InterviewStart[🤖 AI 면접관 연결]
    InterviewStart --> ChatLoop["인터뷰 진행 (Q&A)"]
    ChatLoop --> Eval[평가 및 채점]
    
    Eval --> Result{합격 여부?}
    Result -->|Fail| Feedback[피드백 리포트 제공]
    Result -->|Pass| LevelUp[✨ 별(Star) 획득 & DB 업데이트]
    
    Feedback --> Dashboard
    LevelUp --> Dashboard
    
    Dashboard --> CheckTrack{트랙 모든 노드 3성?}
    CheckTrack -->|Yes| BossRaid[☠️ 트랙 마스터 통합 퀴즈]
    BossRaid --> BossResult{성공?}
    BossResult -->|Yes| GoldGlow[🌟 Golden Glow 이펙트 해금]
    BossResult -->|No| Retry[재도전]
```

## 2. 상세 흐름 설명

### 🟢 Phase 1: Onboarding (진입 및 초기 세팅)
사용자가 서비스에 처음 들어왔을 때, 빈 화면이 아닌 자신의 수준에 맞는 Tech Tree를 마주하도록 유도합니다.

1.  **로그인/회원가입**: 소셜 로그인 등을 통해 접속.
2.  **초기 역량 배치고사 (Calibration)**:
    *   일일이 1레벨(별 1개)을 따는 지루함을 방지하기 위한 "배치고사" 개념.
    *   사용자가 자신의 직무와 사용 가능한 기술 스택을 체크.
    *   기술 당 2-3 문항의 핵심 퀴즈 풀이.
    *   **결과**: 통과한 기술들에 대해 즉시 **'1차 전직(⭐)'** 상태 부여.

### 🔵 Phase 2: Skill Advancement (승급 심사)
가장 핵심적인 이용 흐름으로, AI 면접관과 대화하며 자신의 실력을 증명합니다.

1.  **노드 선택**: 대시보드에서 `Python`이나 `Docker` 같은 기술 아이콘 클릭.
2.  **등급 선택**:
    *   현재 자신의 등급보다 한 단계 높은 등급만 도전 가능.
    *   예: 별 1개(⭐) 보유 시 -> 2차 심사(⭐⭐) 도전 가능.
3.  **AI 인터뷰 진행**:
    *   **2차 심사**: "이 코드가 메모리 누수가 나는 이유는?", "데코레이터를 사용하여 로깅 기능을 구현해보시오." 등의 실무 응용 질문.
    *   **3차 심사**: 아키텍처 설계, 트레이드오프 분석 등 심화 질문.
4.  **평가 및 보상**:
    *   면접 종료 후 AI가 즉시 채점 내용을 분석 리포트로 제공.
    *   **Pass**: 해당 노드에 별 추가, 사용자 경험치 상승.
    *   **Fail**: 부족한 부분에 대한 피드백 및 학습 자료 추천 (Phase 2 예정).

### 🟡 Phase 3: Track Mastery (최종 완성)
특정 직무(예: Backend Track)의 모든 기술을 마스터했을 때 주어지는 최종 도전입니다.

1.  **마스터 조건 달성**: 트랙 내 모든 필수 노드가 3차 전직(⭐⭐⭐) 상태가 됨.
2.  **Boss Challenge (통합 퀴즈)**:
    *   단일 기술이 아닌, 트랙 내 여러 기술이 복합된 시나리오 문제 출제.
    *   예: "Django와 Redis를 사용하여 실시간 채팅 서버를 구축할 때의 동시성 처리 전략을 설명하시오."
3.  **Golden Glow**:
    *   시험 통과 시 해당 트랙의 모든 라인이 **황금색으로 빛나는 시각적 효과** 부여.
    *   사용자가 스크린샷을 찍어 공유하고 싶게 만드는 "Whaaaat" 모먼트 제공.

## 3. 예외 상황 처리 (Exception Flows)

개발 시 고려해야 할 엣지 케이스(Edge Case)입니다.

1. **면접 중 이탈**: 사용자가 브라우저를 닫거나 네트워크가 끊길 경우, 해당 세션은 '평가 없음'으로 처리하고 DB에 기록하지 않음.
2. **API 타임아웃**: AI 응답이 15초 이상 지연될 경우, "면접관이 생각에 잠겼습니다..." 메시지 노출 후 재시도 버튼 제공.
3. **배치고사 스킵**: 신입 개발자가 배치고사를 원치 않을 경우, 모든 노드가 0레벨(Locked)인 상태인 'Newbie Mode'로 시작 가능.