# AI TechTree API 명세서

## 1. 개요
본 문서는 **Agentic Interview System**의 대화형 API (실시간 스트리밍) 명세를 정의합니다. LangGraph 기반 에이전트 워크플로우를 통해 라우팅, 키워드 검색, 퀴즈 출제, 채점, 추천 등의 동작 결과를 프론트엔드로 실시간 전달합니다.

---

## 2. API 엔드포인트

### 📟 인터뷰 실시간 스트리밍
사용자의 메시지(의도)를 분석하여 에이전트의 노드별 실행 상태를 실시간(SSE)으로 수신합니다.

#### Request

- **URL**: `POST /api/chat/stream`
- **Content-Type**: `application/json`
- **Accept**: `text/event-stream`

##### Request Body
| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `message` | `string` | Yes | 사용자가 입력한 메시지 (단순 잡담, 키워드 검색, 퀴즈 답변 등) |
| `thread_id` | `string` | No | 세션 유지를 위한 고유 ID. 입력하지 않으면 `default_session`으로 처리됨. |

##### Request Example (cURL)
```bash
curl -X POST http://localhost:8000/api/chat/stream \
-H "Accept: text/event-stream" \
-H "Content-Type: application/json" \
-d '{
  "message": "Python 퀴즈 내줘",
  "thread_id": "session_uuid_1234"
}'
```

---

#### Response

- **HTTP Status**: `200 OK`
- **Content-Type**: `text/event-stream`
- **Cache-Control**: `no-cache`
- **Connection**: `keep-alive`

##### Response Body (SSE Format)
스트림 데이터는 `data: ` 프리픽스를 포함한 JSON 문자열 형태로 전송됩니다. LangGraph 워크플로우 상의 각 Node가 실행될 때마다 State 객체의 업데이트분이 수신됩니다.

##### 백엔드 구현 기반 주요 노드(Node) 목록
1. **`router`**: 유저 메시지 의도 분석 (`CHIT_CHAT`, `KEYWORD_SEARCH`, `QUIZ`, `ANSWER`, `RECOMMEND`)
2. **`chit_chat`**: 단순 잡담 처리
3. **`search_keyword`**: 키워드 정보 검색 및 상태 업데이트
4. **`generate_quiz`**: 해당 키워드에 대한 퀴즈 출제
5. **`answer_quiz`**: 이전 퀴즈에 대한 정답 평가 및 피드백 생성
6. **`report_star`**: 퀴즈 종료 시 결과 및 보상 리포트 생성
7. **`recommend_keyword`**: 다음 학습 키워드 추천

---

##### 주요 노드별 수신 데이터(Payload) 구조 예시

**1. 퀴즈 생성 단계 (`generate_quiz`)**
```json
data: {
  "generate_quiz": {
    "current_question": {
      "question_text": "Python에서 리스트와 튜플의 차이점은?",
      "options": ["A", "B", "C"],  // 주관식일 경우 null (⚠️ Not Yet)
      "answer": "정답 텍스트 및 해설"
    },
    "quiz_in_progress": true,
    "messages": [
      {
        "type": "ai",
        "content": "### 주제: Python\nQ. Python에서..."
      }
    ]
  }
}
```

**2. 퀴즈 평가 단계 (`answer_quiz`)**
```json
data: {
  "answer_quiz": {
    "pass_fail": "pass", // "pass" 또는 "fail"
    "quiz_count": 2, // 현재 푼 퀴즈 개수
    "messages": [
      {
        "type": "ai",
        "content": "정답입니다! 부연 설명을 하자면..."
      }
    ]
  }
}
```

**3. 잡담 단계 (`chit_chat`)**
```json
data: {
  "chit_chat": {
    "messages": [
      {
        "type": "ai",
        "content": "도움이 필요하시면 언제든지 말씀해주세요."
      }
    ]
  }
}
```

---

## 3. 에러(Error) 처리
통신 중 예외 발생 시 에러 메시지를 스트림 형태로 전송 후 연결을 종료합니다.

| Error Code | Summary | Description |
| :--- | :--- | :--- |
| `400` | Bad Request | `message`가 비어있을 때 발생 (FastAPI `HTTPException` 발생) |
| `-` | Stream Error | 스트리밍 진행 중 에이전트 런타임 에러 발생 시 |

**Stream Error Response Example:**
```json
data: {
  "error": "에이전트 실행 중 오류가 발생했습니다."
}
```

---

## 4. 스트림 종료 정책 및 제약사항

*   **연결 종료 시점**: 백엔드 워크플로우의 실행이 `END` 노드에 도달하면 FastAPI의 제너레이터가 자연히 종료되며 Connection이 닫힙니다. 프론트엔드는 HTTP 리더의 `done: true` 속성으로 완료를 인지합니다.
*   **권한 및 인증 (⚠️ Not Yet)**: 현재 엔드포인트에 대한 JWT 토큰 등의 인증 절차가 요구되지 않습니다.
*   **사용자 관리 (⚠️ Not Yet)**: State 상에 `user_id`, `user_db_id`가 정의되어 있으나 아직 세션 관리 및 DB 연동 시 활발하게 로드되지 않습니다. (추후 토큰 등을 통한 식별 필요)