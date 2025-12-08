# User Flow (서비스 흐름도)
>본 문서는 사용자가 서비스에 진입하여 **AI 면접관과의 상호작용**을 통해 자신의 Tech Tree를 완성해나가는 유저 시나리오를 정의합니다.

## 📌 개요
>서비스 흐름은 크게 세 가지 단계의 유기적인 연결로 구성됩니다.
1. **🟢 온보딩 (Onboarding)**: 배치고사를 통해 사용자의 현재 실력을 빠르게 진단하고 초기 시작점(Tech Tree)을 설정합니다.
2. **🔵 성장 루프 (Growth Loop)**: 원하는 기술 노드를 선택하여 AI 심층 면접을 진행하고, 즉각적인 피드백과 함께 승급(별 획득)에 도전합니다.
3. **🟡 마스터리 (Mastery)**: 트랙 내 모든 기술을 정복한 후, 트랙 마스터 챌린지(통합 퀴즈)를 통해 'Golden Glow'라는 시각적 명예를 획득합니다.

## 1. Flowchart Overview (Mermaid)

```mermaid
graph TD
    %% --- [Color Palette Definition] ---
    classDef default fill:#fff,stroke:#333,stroke-width:1px;
    classDef init fill:#e3f2fd,stroke:#1e88e5,stroke-width:2px,color:#0d47a1;
    classDef main fill:#e8f5e9,stroke:#43a047,stroke-width:2px,color:#1b5e20;
    classDef ai fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px,color:#4a148c;
    classDef gold fill:#fff8e1,stroke:#ff8f00,stroke-width:2px,color:#bf360c;
    classDef fail fill:#ffebee,stroke:#e53935,stroke-width:2px,color:#b71c1c;

    %% Nodes
    Start((Start)) --> Landing[랜딩 페이지]
    Landing --> Login[로그인/회원가입]
    
    Login --> HasAccount{계정 존재?}
    HasAccount -->|No| InitTest["📝 역량 배치고사<br/>(레벨 측정)"]:::init
    HasAccount -->|Yes| Dashboard[🌳 Tech Tree 대시보드]:::main
    
    %% [Reflect]
    Dashboard -->|실력 재측정 요청| InitTest
    InitTest -->|결과 분석| SetBaseStats["기본 레벨<br/>부여/갱신"]:::init
    SetBaseStats --> Dashboard
    
    Dashboard --> ClickNode[노드/기술 선택]
    ClickNode --> CheckStatus{상태 확인}
    
    CheckStatus -->|Locked| Disabled["진입 불가<br/>(선행 학습 필요)"]:::fail
    CheckStatus -->|Available| SelectLevel["도전 등급 선택<br/>(2차/3차)"]
    CheckStatus -->|Mastered| Review["복습 하기<br/>기록 보기"]
    
    SelectLevel --> InterviewStart[🤖 AI 면접관 연결]:::ai
    InterviewStart --> ChatLoop["인터뷰 진행<br/>(Streaming Q&A)"]:::ai
    ChatLoop --> Eval["평가 및 채점<br/>(One-Shot JSON)"]:::ai
    
    %% [Unified]
    Eval --> ResultReport["📄 결과 리포트 확인<br/>(점수/피드백)"]:::main
    
    %% [Conditional]
    ResultReport --> CheckPass{"기준 점수<br/>달성?"}
    
    CheckPass -->|"No (Fail)"| RetryGuide["재도전 가이드 확인"]:::fail
    CheckPass -->|"Yes (Pass)"| StarGet["승급 확정<br/>& 별 지급"]:::gold
    
    RetryGuide --> Dashboard
    StarGet --> Dashboard
    
    Dashboard --> CheckTrack{"트랙 모든 노드 3성?"}
    CheckTrack -->|Yes| BossRaid["☠️ 트랙 마스터<br/>통합 퀴즈"]:::gold
    BossRaid --> BossResult{"성공?"}
    
    BossResult -->|Yes| GoldGlow["🌟 Golden Glow<br/>이펙트 해금"]:::gold
    BossResult -->|No| Retry["재도전<br/>(쿨타임)"]:::fail

    %% [Viral Loop]
    StarGet --> Share["SNS 공유하기<br/>(자랑하기)"]:::main
    GoldGlow --> Share
    Share --> Dashboard

    %% [UI Fix] Spacer
    Share ~~~ Spacer1[ ]
    style Spacer1 fill:none,stroke:none,color:#00000000,height:50px
```

## 2. 상세 흐름 설명

### 🟢 Phase 1: Onboarding (진입 및 초기 세팅)
사용자가 서비스에 처음 들어왔을 때, 빈 화면이 아닌 자신의 수준에 맞는 Tech Tree를 마주하도록 유도합니다.

1.  **로그인/회원가입**: 소셜 로그인 등을 통해 접속.
2.  **초기 역량 배치고사 (Calibration)**:
    *   일일이 1레벨(별 1개)을 따는 지루함을 방지하기 위한 "실력 진단" 개념.
    *   사용자가 자신의 직무와 사용 가능한 기술 스택을 체크.
    *   **기술 당 2~3문항**의 핵심 퀴즈 풀이.
    *   **결과**: 통과한 기술들에 대해 즉시 **'1차 전직(⭐)'** 상태 부여. (추후 대시보드에서 재응시 가능)

### 🔵 Phase 2: Skill Advancement (승급 심사)
가장 핵심적인 이용 흐름으로, AI 면접관과 대화하며 자신의 실력을 증명합니다.

1.  **노드 선택**: 대시보드에서 `Python`이나 `Docker` 같은 기술 아이콘 클릭.
2.  **등급 선택**:
    *   현재 자신의 등급보다 한 단계 높은 등급만 도전 가능.
    *   예: 별 1개(⭐) 보유 시 -> 2차 심사(⭐⭐) 도전 가능.
3.  **AI 인터뷰 진행 (Streaming Q&A)**:
    *   **2차 심사**: "이 코드가 메모리 누수가 나는 이유는?" 등의 실무 응용 질문.
    *   **3차 심사**: 아키텍처 설계, 트레이드오프 분석 등 심화 질문.
    *   답변이 지연되지 않도록 스트리밍 방식으로 질문/피드백 제공.
4.  **평가 및 결과 리포트 (Unified Feedback)**:
    *   면접 종료 후 AI가 채점한 결과를 **하나의 통합된 리포트 페이지**에서 확인합니다.
    *   **합격 시 (Pass)**: 축하 메시지, 획득한 별(Star) 표시, 그리고 더 나은 코드를 위한 'Pro Tip'.
    *   **불합격 시 (Fail)**: 부족한 핵심 개념과 구체적인 학습 방향 가이드가 제공됩니다.
    *   사용자는 결과를 확인한 후 대시보드로 복귀합니다.

### 🟡 Phase 3: Track Mastery (최종 완성)
특정 직무(예: Backend Track)의 모든 기술을 마스터했을 때 주어지는 최종 도전입니다.

1.  **마스터 조건 달성**: 트랙 내 모든 필수 노드가 3차 전직(⭐⭐⭐) 상태가 됨.
2.  **Track Master Challenge**:
    *   단일 기술이 아닌, 트랙 내 여러 기술이 복합된 시나리오 문제 출제.
    *   예: "Django와 Redis를 사용하여 실시간 채팅 서버를 구축할 때의 동시성 처리 전략을 설명하시오."
3.  **Golden Glow**:
    *   시험 통과 시 해당 트랙의 모든 라인이 **황금색으로 빛나는 시각적 효과** 부여.
    *   사용자가 스크린샷을 찍어 공유하고 싶게 만드는 **"자랑하기"** 모먼트 제공.
    *   **실패 시**: 일정 시간(쿨타임) 후 재도전 기회 부여.

## 3. 예외 상황 처리 (Exception Flows)

개발 시 고려해야 할 엣지 케이스(Edge Case)입니다.

1. **면접 중 이탈**: 사용자가 브라우저를 닫거나 네트워크가 끊길 경우, 해당 세션은 '평가 없음'으로 처리하고 DB에 기록하지 않음.
2. **API 타임아웃**: AI 응답이 15초 이상 지연될 경우, "면접관이 생각에 잠겼습니다..." 메시지 노출 후 재시도 버튼 제공.
3. **배치고사 스킵**: 신입 개발자가 배치고사를 원치 않을 경우, 모든 노드가 0레벨(Locked)인 상태인 'Newbie Mode'로 시작 가능.