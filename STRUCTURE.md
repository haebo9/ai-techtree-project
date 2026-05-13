# Project Structure

Current runtime path: **FastAPI + LangGraph + OpenAI Realtime + Next.js**.

```text
.
├── AGENTS.md
├── GUIDE.md
├── README.md
├── STRUCTURE.md
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entrypoint and CORS
│   │   ├── api/
│   │   │   ├── router.py            # /api router aggregation
│   │   │   ├── interview.py         # Realtime session, tool calls, evaluation, email
│   │   │   └── upload.py            # Resume/job posting parsing
│   │   ├── core/
│   │   │   ├── config.py            # Environment settings
│   │   │   ├── llm.py               # ChatOpenAI factory
│   │   │   └── logger.py            # App logging and optional Telegram alerts
│   │   ├── engine/
│   │   │   ├── graphs/              # LangGraph state/workflow
│   │   │   ├── nodes/               # Interviewer/evaluator nodes
│   │   │   ├── prompts/             # Realtime and reflection prompts
│   │   │   └── tools/               # Tavily-backed job search
│   │   ├── schemas_api/             # FastAPI request/response DTOs
│   │   ├── services/                # Reflection memory stores/services
│   │   └── source/                  # Local reflection memory files
│   ├── scripts/
│   │   └── setup_reflection_db.py   # Optional Mongo reflection index setup
│   ├── tests/                       # Focused backend regression tests
│   ├── langgraph.json
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Interview setup form
│   │   ├── interview/page.tsx       # WebRTC Realtime interview
│   │   ├── result/page.tsx          # Report view
│   │   ├── complete/page.tsx        # Evaluation waiting/complete flow
│   │   └── debug/page.tsx           # Developer Realtime diagnostics
│   ├── lib/
│   │   └── interviewClosing.js
│   ├── public/
│   │   ├── logo.png
│   │   └── dummy/                   # Debug page sample inputs
│   ├── package.json
│   └── tsconfig.json
└── docs/                            # Product and architecture notes
```
