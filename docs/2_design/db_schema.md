# Database Schema Design (MongoDB)

- **[1. Overview](#1-overview)**
- **[2. Collections Specification](#2-collections-specification)**
- **[3. Data Access Patterns](#3-data-access-patterns)**

---

## 1. Overview
>본 문서는 **AI TechTree** 프로젝트의 데이터 모델을 정의합니다.
>단순한 선형적 학습이 아닌, **사용자의 선택에 따라 분기(Branching)되고 확장되는 그래프 형태의 로드맵**을 지원하기 위해 설계되었습니다.

> **MongoDB Atlas (NoSQL)의 유연한 스키마를 활용하여 다음과 같은 핵심 가치를 제공합니다**
> 1.  **Flexible Paths**: 필수 기술뿐만 아니라 대체 기술이나 선택적 분기(OR)를 표현할 수 있는 구조.
> 2.  **Read Optimized**: 대시보드 진입 시 복잡한 조인 없이 **단 1회의 쿼리**로 전체 트리의 진행 상황을 로드.
> 3.  **Atomic Progression**: 면접 합격 시 사용자의 기술 레벨과 별(Star) 획득을 원자적(Atomic)으로 업데이트.
>---
> ### 📌 Key Design Decisions
> 1.  **Skill Tree Embedding**: 사용자(`users`) 컬렉션 내에 학습 현황(`skill_tree`)을 내장하여, 대시보드 렌더링 속도를 극대화합니다.
> 2.  **Graph-based Track Definition**: 트랙(`tracks`) 메타데이터에 `group_id`와 `dependency_logic(OR)`을 도입하여, 비선형적인 학습 경로를 지원합니다.
> 3.  **Snapshot-based Interview**: 면접 기록은 완료 시점에 하나의 문서(`interviews`)로 스냅샷 저장하여, 데이터 무결성과 조회 성능을 보장합니다.

---

## 2. Collections Specification
- [**2.1 users** (사용자/학습현황)](#21-users-사용자-및-학습-현황)
- [**2.2 interviews** (면접/평가)](#22-interviews-면접-로그-및-평가)
- [**2.3 tracks** (트랙/로드맵)](#23-tracks-트랙-메타데이터) 
- [**2.4 skills** (기술 정보)](#24-skills-기술-메타데이터) 
- [**2.5 questions** (질문 은행)](#25-questions-면접-질문-은행) 
### 2.1 `users` (사용자 및 학습 현황)
사용자의 계정 정보와 **기술 트리 진행 상황**을 관리하는 핵심 컬렉션입니다.

* **Index**: `{"auth.email": 1}` (Unique), `{"auth.uid": 1}`

```javascript
{
  "_id": ObjectId("..."),
  "auth": {
    "email": "user@example.com",     // 로그인 ID (이메일)
    "provider": "kakao",             // 소셜 로그인 제공자
    "uid": "123456789"               // 제공자 측 고유 ID
  },
  "profile": {
    "nickname": "AI_Master",
    "avatar_url": "https://...",
    "job_title": "Student"           // 희망 직무 (Optional)
  },
  "stats": {
    "total_stars": 12,               // 획득한 총 별 개수 (랭킹용)
    "completed_tracks": [            // 마스터한 트랙 ID (Golden Glow 효과)
      "backend-developer"
    ]
  },
  /**
   * [Core] 기술 습득 현황 (Map 구조)
   * Key: skill_slug (e.g., 'python') -> 빠른 접근(O(1))을 위해 Map 사용
   */
  "skill_tree": {
    "python": {"order": 1,                   // 시각화 순서
      "level": 2,                    // 현재 레벨 (0:Locked, 1:Basic, 2:Adv, 3:Master)
      "stars": 2,                    // UI에 표시될 별 개수
      "last_tested_at": ISODate("...") // 마지막 승급 심사일
    },
    "docker": {
      "level": 1,
      "stars": 1,
      "last_tested_at": ISODate("...")
    }
  },
  "created_at": ISODate("..."),
  "updated_at": ISODate("...")
}
```

### 2.2 `interviews` (면접 로그 및 평가)

AI 면접관과의 대화 기록 및 최종 평가 결과를 저장합니다.

* **Index**: `{"user_id": 1}` (내 기록 조회용), `{"meta.status": 1}`

```javascript
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),       // users._id 참조
  "meta": {
    "skill_slug": "python",         // 대상 기술
    "track_slug": "backend",        // (Optional) 어떤 트랙 문맥인가
    "target_level": 2,              // 도전한 레벨 (1, 2, 3)
    "status": "COMPLETED",          // IN_PROGRESS, COMPLETED, FAILED
    "started_at": ISODate("..."),
    "ended_at": ISODate("...")
  },
  /**
   * 대화 로그 전체 저장 (Context 재구성용)
   */
  "messages": [
    {
      "role": "assistant",
      "content": "Python의 데코레이터에 대해 설명해주세요.",
      "timestamp": ISODate("...")
    },
    {
      "role": "user",
      "content": "함수를 수정하지 않고 기능을 확장할 때 사용합니다...",
      "timestamp": ISODate("...")
    }
  ],
  /**
   * One-Shot Evaluation 결과 (JSON)
   */
  "result": {
    "is_passed": true,              // 합격 여부
    "score": 85,                    // 점수 (0~100)
    "feedback_message": "핵심 개념을 잘 이해하고 있습니다.",
    "improvement_tip": "functools.wraps를 사용하는 이유도 같이 언급하면 좋습니다.",
    "evaluated_at": ISODate("...")
  }
}
```

### 2.3 `tracks` (트랙 메타데이터)

직무별 로드맵(트랙) 구조를 정의합니다. (Read-Only 성격)

* **Index**: `{"slug": 1}` (Unique)

```javascript
{
  "_id": ObjectId("..."),
  "slug": "backend-developer",      // URL 식별자 (ex: /track/backend-developer)
  "title": "Backend Developer",
  "description": "서버 개발의 기초부터 배포까지 마스터하는 코스",
  "nodes": [
{
  "_id": ObjectId("..."),
  "slug": "backend-developer",
  "title": "Backend Developer",
  "nodes": [
    {
      "skill_slug": "python",
      "required_level": 3,
      "dependencies": [] 
    },
    // [선택 분기] 사용자는 RDBMS 또는 NoSQL 중 하나만 마스터해도 다음 단계로 진행 가능
    {
      "skill_slug": "postgresql",
      "group_id": "database_selection", // 같은 그룹 ID를 가진 노드들은 '선택지'로 묶임
      "required_level": 2,
      "dependencies": ["python"]
    },
    {
      "skill_slug": "mongodb",
      "group_id": "database_selection", // PostgreSQL 대신 MongoDB를 선택해도 됨
      "required_level": 2,
      "dependencies": ["python"]
    },
    // 다음 단계: 위 DB 중 *하나라도* 조건을 만족하면 해금됨
    {
      "skill_slug": "fastapi",
      "dependencies": ["postgresql", "mongodb"], // 의존성 배열에 나열된 것 중 '하나(OR)'만 만족하면 됨
      "dependency_logic": "OR" // 기본값은 AND이나, OR로 명시하여 선택적 진행 지원
    }
  ]
}
```

### 2.4 `skills` (기술 메타데이터)

>개별 기술에 대한 상세 정보입니다.

* **Index**: `{"slug": 1}` (Unique)

```javascript
{
  "_id": ObjectId("..."),
  "slug": "python",                 // 고유 식별자
  "name": "Python",
  "category": "Language",           // Language, Framework, Infrastructure...
  "icon_url": "/assets/icons/python.svg",
  "description": "AI 및 백엔드 개발의 표준 언어"
}
```

### 2.5 `questions` (면접 질문 은행)
>기술별/레벨별 검증된 질문과 모범 답안을 저장합니다.

* **Index**: `{"skill_slug": 1, "level": 1}`

```javascript
{
  "_id": ObjectId("..."),
  "skill_slug": "python",
  "level": 2, // 2차 승급 (Applied Level) 질문
  "topic": "Generator & Iterator",
  "question_text": "Python의 Generator가 일반 함수와 다른 점은 무엇이며, 메모리 관점에서 어떤 이점이 있나요?",
  "model_answer": "Generator는 yield 키워드를 사용하여 데이터를 한 번에 하나씩 반환하며...",
  "evaluation_criteria": [ // 채점 시 참고할 핵심 키워드
    "lazy evaluation",
    "yield",
    "memory efficiency"
  ]
}
```

---

## 3. Data Access Patterns

### ✅ Q1. 대시보드 로딩 (가장 빈번)

* **Query**: `db.users.findOne({ "auth.uid": current_uid })`
* **Logic**: 유저 문서를 통째로 가져와 `skill_tree` 필드를 순회하며 프론트엔드 그래프(React Flow)의 노드 색상과 별 개수를 렌더링합니다. (추가 쿼리 없음)

### ✅ Q2. 면접 시작

* **Query**: `db.interviews.insertOne({ user_id: ..., meta: { status: 'IN_PROGRESS' ... } })`
* **Logic**: 새로운 면접 세션을 생성하고 `_id`를 반환하여 채팅방을 엽니다.

### ✅ Q3. 면접 종료 및 승급

1.  **Update**: `db.interviews.updateOne({ _id: ... }, { $set: { "result": ..., "meta.status": "COMPLETED" } })`
2.  **If Passed**:
    ```javascript
    db.users.updateOne(
      { _id: user_id },
      { 
        $set: { "skill_tree.python.level": 2, "skill_tree.python.stars": 2 },
        $inc: { "stats.total_stars": 1 }
      }
    )
    ```
    * **Atomic Update**: MongoDB의 `$set` 연산자를 사용하여 동시성 문제 없이 안전하게 레벨을 업데이트합니다.
