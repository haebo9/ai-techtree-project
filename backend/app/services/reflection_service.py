import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field, ValidationError
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.core.llm import get_llm
from app.core.logger import get_logger

logger = get_logger(__name__)


def _default_store_path() -> Path:
    configured_path = Path(settings.REFLECTION_STORE_PATH)
    if configured_path.is_absolute():
        return configured_path

    if configured_path.parts and configured_path.parts[0] == "backend":
        project_root = Path(__file__).resolve().parents[3]
        return project_root / configured_path

    return Path.cwd() / configured_path


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _profile_tokens(*values: str) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        normalized = _normalize_key(value)
        if not normalized:
            continue
        tokens.update(token for token in re.split(r"[^0-9a-zA-Z가-힣+.#]+", normalized) if token)
    return tokens


class ReflectionItem(BaseModel):
    id: str
    created_at: str
    job_title: str = ""
    experience: str = ""
    education: str = ""
    tags: List[str] = Field(default_factory=list)
    issue: str = ""
    lesson: str = ""
    prompt_hint: str
    confidence: float = 0.0
    source_session_id: str = ""


class ReflectionCandidate(BaseModel):
    tags: List[str] = Field(default_factory=list)
    issue: str = Field(default="", description="이번 면접에서 관찰된 면접 운영상의 문제")
    lesson: str = Field(default="", description="다음 면접에 재사용할 수 있는 학습 내용")
    prompt_hint: str = Field(default="", description="면접관 시스템 프롬프트에 넣을 짧은 운영 지침")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ReflectionGeneration(BaseModel):
    reflections: List[ReflectionCandidate] = Field(default_factory=list)


class ReflectionStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or _default_store_path()

    def read_all(self) -> List[ReflectionItem]:
        if not self.path.exists():
            return []

        reflections: List[ReflectionItem] = []
        with self.path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    reflections.append(ReflectionItem.model_validate_json(raw))
                except (ValidationError, ValueError) as exc:
                    logger.warning("Skipping invalid reflection line %s: %s", line_number, exc)
        return reflections

    def append(self, item: ReflectionItem) -> bool:
        if not _normalize_key(item.prompt_hint):
            return False

        existing_hints = {_normalize_key(reflection.prompt_hint) for reflection in self.read_all()}
        if _normalize_key(item.prompt_hint) in existing_hints:
            return False

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(item.model_dump_json(ensure_ascii=False) + "\n")
        return True

    def search(
        self,
        job_title: str,
        experience: str = "",
        education: str = "",
        limit: int = 5,
    ) -> List[ReflectionItem]:
        profile_tokens = _profile_tokens(job_title, experience, education)
        normalized_job_title = _normalize_key(job_title)
        normalized_experience = _normalize_key(experience)
        normalized_education = _normalize_key(education)

        scored: List[tuple[int, str, ReflectionItem]] = []
        for reflection in self.read_all():
            score = 0
            reflection_job_title = _normalize_key(reflection.job_title)
            reflection_experience = _normalize_key(reflection.experience)
            reflection_education = _normalize_key(reflection.education)
            reflection_tokens = _profile_tokens(
                reflection.job_title,
                reflection.experience,
                reflection.education,
                " ".join(reflection.tags),
            )

            if normalized_job_title and reflection_job_title:
                if normalized_job_title in reflection_job_title or reflection_job_title in normalized_job_title:
                    score += 8
                elif profile_tokens & reflection_tokens:
                    score += 4
            elif profile_tokens & reflection_tokens:
                score += 2

            if normalized_experience and normalized_experience == reflection_experience:
                score += 3
            elif normalized_experience and reflection_experience and (
                normalized_experience in reflection_experience or reflection_experience in normalized_experience
            ):
                score += 2

            if normalized_education and normalized_education == reflection_education:
                score += 1

            if reflection.confidence >= 0.7:
                score += 1

            if score > 0:
                scored.append((score, reflection.created_at, reflection))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [reflection for _, _, reflection in scored[:limit]]


class ReflectionService:
    def __init__(self, store: Optional[ReflectionStore] = None):
        self.store = store or ReflectionStore()

    def get_prompt_guidelines(
        self,
        job_title: str,
        experience: str = "",
        education: str = "",
        limit: int = 5,
    ) -> str:
        reflections = self.store.search(
            job_title=job_title,
            experience=experience,
            education=education,
            limit=limit,
        )
        return format_reflection_guidelines(reflections)

    def generate_and_store(
        self,
        *,
        session_id: str,
        job_title: str,
        experience: str,
        education: str,
        messages: Iterable[Any],
        evaluation: Dict[str, Any],
        saved_jobs: List[Dict[str, Any]],
    ) -> int:
        candidates = self._generate_candidates(
            job_title=job_title,
            experience=experience,
            education=education,
            messages=messages,
            evaluation=evaluation,
            saved_jobs=saved_jobs,
        )

        stored_count = 0
        for candidate in candidates:
            if candidate.confidence < 0.55 or not _normalize_key(candidate.prompt_hint):
                continue

            item = ReflectionItem(
                id=str(uuid.uuid4()),
                created_at=datetime.now(timezone.utc).isoformat(),
                job_title=job_title or "",
                experience=experience or "",
                education=education or "",
                tags=[tag.strip() for tag in candidate.tags if tag.strip()][:6],
                issue=_redact_sensitive_text(candidate.issue.strip()),
                lesson=_redact_sensitive_text(candidate.lesson.strip()),
                prompt_hint=_compact_prompt_hint(candidate.prompt_hint),
                confidence=round(float(candidate.confidence), 2),
                source_session_id=session_id,
            )
            if self.store.append(item):
                stored_count += 1

        return stored_count

    def _generate_candidates(
        self,
        *,
        job_title: str,
        experience: str,
        education: str,
        messages: Iterable[Any],
        evaluation: Dict[str, Any],
        saved_jobs: List[Dict[str, Any]],
    ) -> List[ReflectionCandidate]:
        transcript = _format_messages(messages, max_chars=7000)
        if not transcript:
            return []

        evaluation_summary = json.dumps(evaluation, ensure_ascii=False, default=str)[:3500]
        jobs_summary = json.dumps(saved_jobs[:3], ensure_ascii=False, default=str)[:2000]

        system_prompt = """
당신은 AI 면접관의 운영 품질을 개선하는 Reflexion 분석가입니다.
전체 면접 대화와 평가 결과를 보고, 다음 면접의 시스템 프롬프트에 넣을 수 있는 짧은 운영 지침만 추출하세요.

규칙:
- 지원자의 개인정보, 전체 답변 원문, 이메일, 이름처럼 식별 가능한 정보는 저장하지 마세요.
- 모델 가중치를 바꾸는 것이 아니라 다음 면접에 재사용할 프롬프트 지침을 만드세요.
- 면접관의 질문 방식, 난이도 조절, 공고 요건 반영, 후속 질문 품질을 개선하는 내용만 작성하세요.
- 이미 잘 작동한 일반 원칙이 아니라, 이번 면접에서 실제로 드러난 개선점을 최대 3개만 작성하세요.
- prompt_hint는 면접관에게 직접 명령하는 한 문장으로 작성하세요.
"""
        user_prompt = f"""
[지원자 조건]
- 지원 직무: {job_title or "정보 없음"}
- 경력: {experience or "정보 없음"}
- 학력: {education or "정보 없음"}

[면접 대화]
{transcript}

[평가 결과]
{evaluation_summary}

[검색/추천된 채용 공고]
{jobs_summary}
"""

        llm = get_llm(temperature=0.1)
        structured_llm = llm.with_structured_output(ReflectionGeneration)
        result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        return result.reflections[:3]


def format_reflection_guidelines(reflections: List[ReflectionItem]) -> str:
    if not reflections:
        return ""

    bullets = []
    seen: set[str] = set()
    for reflection in reflections:
        hint = _compact_prompt_hint(reflection.prompt_hint)
        normalized = _normalize_key(hint)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        bullets.append(f"- {hint}")

    if not bullets:
        return ""

    return "\n# 이전 면접에서 학습한 운영 지침\n" + "\n".join(bullets)


def safe_generate_and_store_reflections(
    *,
    session_id: str,
    job_title: str,
    experience: str,
    education: str,
    messages: Iterable[Any],
    evaluation: Dict[str, Any],
    saved_jobs: List[Dict[str, Any]],
) -> int:
    try:
        return ReflectionService().generate_and_store(
            session_id=session_id,
            job_title=job_title,
            experience=experience,
            education=education,
            messages=messages,
            evaluation=evaluation,
            saved_jobs=saved_jobs,
        )
    except Exception as exc:
        logger.warning("Reflection generation failed for session %s: %s", session_id, exc)
        return 0


def _format_messages(messages: Iterable[Any], max_chars: int) -> str:
    rows = []
    for message in messages:
        role = "면접관" if message.__class__.__name__ == "AIMessage" else "지원자"
        content = getattr(message, "content", "")
        if not content:
            continue
        rows.append(f"{role}: {str(content).strip()}")

    transcript = "\n".join(rows)
    if len(transcript) <= max_chars:
        return transcript
    return transcript[-max_chars:]


def _compact_prompt_hint(value: str) -> str:
    hint = _redact_sensitive_text(re.sub(r"\s+", " ", (value or "").strip()))
    return hint[:220]


def _redact_sensitive_text(value: str) -> str:
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email]", value or "")
    return re.sub(r"\b\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{4}\b", "[phone]", text)
