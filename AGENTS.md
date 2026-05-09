# AGENTS.md

This document is the working guide for AI coding agents contributing to TechTree.
Treat the codebase as a live MVP: prefer small, verified changes that keep the interview flow working end to end.

## Project Overview

TechTree is an AI mock interview service. The current product flow is:

1. The user enters a target role, experience, education, resume, and optional job posting text/image in the Next.js frontend.
2. The backend analyzes uploaded resumes/job postings and starts an OpenAI Realtime interview session.
3. The interview page connects to OpenAI Realtime over WebRTC and supports push-to-talk voice answers.
4. During the interview, OpenAI may call `search_job_postings`; the frontend executes the backend Tavily search endpoint and returns structured job postings to the Realtime session.
5. When the interview ends, transcripts and saved job postings are sent to the backend LangGraph evaluator.
6. The result page shows score, strengths, weaknesses, Q&A feedback, and recommended job postings.

The codebase still contains some older v1.0/v1.1 documentation and Docker/Streamlit references. When instructions conflict, follow the current code path: `FastAPI + LangGraph + OpenAI Realtime + Next.js`.

## Repository Map

- `frontend/`: Next.js 16 app router frontend.
- `frontend/app/page.tsx`: profile, resume upload, job posting upload/text input, localStorage handoff.
- `frontend/app/interview/page.tsx`: WebRTC OpenAI Realtime interview, tool-call handling, transcript capture, end-interview API call.
- `frontend/app/result/page.tsx`: final report UI and email-send trigger.
- `frontend/app/debug/page.tsx`: developer WebRTC/debug page with realtime logs.
- `backend/app/main.py`: FastAPI app entrypoint and CORS setup.
- `backend/app/api/router.py`: includes `/api/interview` and `/api/upload`.
- `backend/app/api/interview.py`: Realtime session creation, search tool endpoint, end-evaluation endpoint, email endpoint.
- `backend/app/api/upload.py`: PDF parsing and job posting title extraction from text/image.
- `backend/app/engine/graphs/`: LangGraph state and workflow.
- `backend/app/engine/nodes/interviewer.py`: LangGraph interviewer node.
- `backend/app/engine/nodes/evaluator.py`: final evaluation and `job_recommendations` injection.
- `backend/app/engine/tools/job_search.py`: Tavily-backed job posting search tool.
- `backend/app/engine/prompts/api_interviewer.py`: OpenAI Realtime interviewer system prompt.
- `backend/app/core/config.py`: environment settings.
- `backend/app/core/llm.py`: cached `ChatOpenAI` factory.
- `backend/app/services/`, `backend/app/schemas_db/`: MongoDB/user/keyword legacy and supporting service code.
- `docs/`, `README.md`, `STRUCTURE.md`, `dev_log.md`: project documentation; some content may lag behind current implementation.

## Local Setup

Use two terminals for the current app.

Backend:

```bash
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Useful URLs:

- Frontend: `http://localhost:3000`
- Debug page: `http://localhost:3000/debug`
- Backend docs: `http://localhost:8000/docs`

Environment variables are loaded by `backend/app/core/config.py` from `backend/.env`, `.env`, `backend/.env.local`, and `.env.local`.

Required for most backend flows:

- `OPENAI_API_KEY`

Optional, feature-dependent:

- `TAVILY_API_KEY`: real job posting search. Without it, the search tool returns mock structured postings.
- `MONGODB_URL`, `DB_NAME`: database-backed service code.
- `RESEND_API_KEY`: email delivery.
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: Telegram logging.

## Current Runtime Notes

- Frontend fetches the backend with hardcoded `http://localhost:8000` URLs. If deployment/proxy work is requested, update these carefully across pages.
- FastAPI CORS currently allows `http://localhost:3000`.
- OpenAI Realtime session creation happens in `backend/app/api/interview.py`.
- Realtime client connection happens in `frontend/app/interview/page.tsx`.
- Push-to-talk is intentional: microphone track is disabled by default and enabled while the user holds Space.
- `turn_detection` is disabled in the Realtime session, so the frontend manually sends `input_audio_buffer.commit` and `response.create`.
- Job recommendations should be real structured postings, not LLM hallucinations. Keep the evaluator behavior that injects `saved_jobs` into `job_recommendations`.

## Key Data Flows

### Start Interview

`frontend/app/page.tsx`
stores `interviewProfile` in `localStorage`, then navigates to `/interview`.

`frontend/app/interview/page.tsx`
POSTs to:

```text
POST /api/interview/start
```

The backend returns `session_id` and an OpenAI ephemeral token.

### Realtime Job Search

OpenAI Realtime may call:

```text
search_job_postings({ query })
```

The frontend handles `response.function_call_arguments.done`, then POSTs:

```text
POST /api/interview/tools/search_job
```

The backend calls `search_korean_job_postings`. Expected return shape:

```ts
Array<{
  company: string;
  title: string;
  url: string;
  content?: string;
}>
```

The frontend appends array results to `savedJobsRef.current` and returns the same data to Realtime as `function_call_output`.

### End Interview

`frontend/app/interview/page.tsx` POSTs:

```text
POST /api/interview/{session_id}/end
```

Payload:

```ts
{
  transcripts: Array<{ role: "user" | "ai"; text: string }>;
  saved_jobs: Array<Record<string, unknown>>;
}
```

`backend/app/engine/nodes/evaluator.py` converts transcripts to evaluation output and force-injects up to 3 normalized postings into `job_recommendations`.

### Result Report

`frontend/app/result/page.tsx` reads `interviewResult`, `interviewTranscripts`, `interviewDuration`, and `interviewDate` from `localStorage`.

Email sending POSTs to:

```text
POST /api/interview/{session_id}/email
```

## Development Commands

Backend syntax check:

```bash
python3 -m compileall backend/app
```

When using the project virtualenv from the repository root:

```bash
.venv/bin/python -m compileall backend/app
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

LangGraph Studio/dev server, when needed:

```bash
cd backend
langgraph dev --host 0.0.0.0 --port 2024
```

Docker compose files exist, but the local compose file still references an older Streamlit frontend path. Prefer direct `uvicorn` and `npm run dev` for current Next.js work unless the task is explicitly Docker-related.

## Coding Guidelines

- Keep changes focused on the requested flow. Avoid broad refactors unless they unblock the fix.
- Preserve existing user-facing Korean copy unless the task asks for content/design changes.
- Prefer typed request/response shapes. Avoid introducing `any` in frontend TypeScript.
- Backend API schemas live in `backend/app/schemas_api/`; use Pydantic models for new API payloads.
- Keep LLM prompts explicit about output constraints when downstream code depends on structured data.
- Never let the evaluator invent job postings. Use `saved_jobs` or the Tavily tool output only.
- Keep Realtime event handling defensive; event order can vary and some transcripts may be missing.
- Do not commit secrets, `.env` files, generated caches, or uploaded user content.
- There are generated/cache files in the tree such as `__pycache__`; do not expand them or base work on them.

## Frontend Guidelines

- Current app uses Next.js app router, React 19, Tailwind CSS, and some lucide icons.
- The main pages are client components because they use browser APIs, localStorage, FileReader, WebRTC, and media devices.
- Keep controls stable on mobile and desktop. Test long Korean strings and narrow screens when changing UI.
- Resume upload supports PDF/TXT. Job posting image upload supports common image types and HEIC conversion through `heic2any`.
- `/debug` is a developer utility. Keep it useful for Realtime and tool-call diagnosis.

## Backend Guidelines

- FastAPI routes are grouped under `/api`.
- `settings.OPENAI_API_KEY` is required at import/runtime for many flows, because settings are loaded eagerly.
- `get_llm()` defaults to `gpt-4.1`; job posting title extraction currently uses `gpt-5.4-nano` directly in `upload.py`.
- Tavily search is implemented with direct `requests.post` to `https://api.tavily.com/search`.
- If Tavily fails or the key is missing, the search tool should return an empty list or structured mock data, never an unstructured error string for the report path.
- LangGraph state is defined in `backend/app/engine/graphs/state.py`. Add new state fields there before relying on them in nodes.

## Testing Expectations

Before handing off code changes, run the narrowest useful checks:

- Python touched: `python3 -m compileall <changed backend files>` or `python3 -m compileall backend/app`.
- Frontend touched: `cd frontend && npm run lint`.
- Realtime/interview flow touched: manually sanity-check `/`, `/interview`, and `/result` if servers and API keys are available.
- Job recommendation flow touched: verify that `search_job_postings` returns an array and that `job_recommendations` is non-empty when `saved_jobs` is provided.

Known current lint state as of this document:

- `npm run lint` exits with 0 errors, but there are warnings for unused variables, React hook dependencies, and raw `<img>` usage.

## Common Pitfalls

- Do not assume README architecture text is fully current; code is the source of truth.
- Do not change the job search tool back to a plain string summary. The report depends on structured postings.
- Do not remove `savedJobsRef` or the `saved_jobs` payload from the end-interview request.
- Do not rely on the LLM's `job_recommendations` field; the evaluator prompt asks the model to return `[]` and then injects real postings.
- Do not enable automatic VAD casually. The current UX and frontend logic are built around push-to-talk.
- Be careful with base64 job posting images. The frontend stores a `data:image/...;base64,...` URL and sends it to Realtime/upload analysis.
- If tests fail because `python` is missing, try `python3` or the repository virtualenv at `.venv/bin/python`.

## PR Guidelines

- Use a concise title with the affected area, for example `[interview] Preserve searched jobs in final report`.
- In the summary, describe user-visible behavior first, then implementation details.
- Include verification commands and note any checks that could not be run.
- Keep unrelated cleanup out of feature/bugfix PRs.
