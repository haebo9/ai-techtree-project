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


def _resolve_store_path(configured_value: str) -> Path:
    configured_path = Path(configured_value)
    if configured_path.is_absolute():
        return configured_path

    if configured_path.parts and configured_path.parts[0] == "backend":
        project_root = Path(__file__).resolve().parents[3]
        return project_root / configured_path

    return Path.cwd() / configured_path


def _default_reflection_store_path() -> Path:
    return _resolve_store_path(settings.REFLECTION_STORE_PATH)


def _default_policy_store_path() -> Path:
    return _resolve_store_path(settings.POLICY_STORE_PATH)


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


class PolicyItem(BaseModel):
    id: str
    created_at: str
    updated_at: str
    status: str = "candidate"
    scope: str = "role_experience"
    job_title: str = ""
    experience: str = ""
    education: str = ""
    policy: str
    evidence_count: int = 1
    confidence: float = 0.0
    source_reflection_ids: List[str] = Field(default_factory=list)
    supersedes: List[str] = Field(default_factory=list)
    replaced_by: Optional[str] = None
    reason: str = ""


class ReflectionStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or _default_reflection_store_path()

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

        duplicate_key = (_normalize_key(item.source_session_id), _normalize_key(item.prompt_hint))
        existing_keys = {
            (_normalize_key(reflection.source_session_id), _normalize_key(reflection.prompt_hint))
            for reflection in self.read_all()
        }
        if duplicate_key in existing_keys:
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


class PolicyStore:
    promotion_threshold = 3
    min_promoted_confidence = 0.7

    def __init__(self, path: Optional[Path] = None):
        self.path = path or _default_policy_store_path()

    def read_all(self) -> List[PolicyItem]:
        if not self.path.exists():
            return []

        policies: List[PolicyItem] = []
        with self.path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    policies.append(PolicyItem.model_validate_json(raw))
                except (ValidationError, ValueError) as exc:
                    logger.warning("Skipping invalid policy line %s: %s", line_number, exc)
        return policies

    def write_all(self, policies: List[PolicyItem]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            for policy in policies:
                file.write(policy.model_dump_json(ensure_ascii=False) + "\n")

    def consolidate(self, reflections: List[ReflectionItem]) -> List[PolicyItem]:
        policies = self.read_all()
        existing_reflection_ids = {
            reflection_id
            for policy in policies
            for reflection_id in policy.source_reflection_ids
        }

        changed = False
        for reflection in reflections:
            if reflection.id in existing_reflection_ids:
                continue
            if reflection.confidence < 0.55 or not _normalize_key(reflection.prompt_hint):
                continue

            changed = True
            matched_policy = self._find_matching_policy(policies, reflection)
            if matched_policy:
                _merge_reflection_into_policy(matched_policy, reflection)
            else:
                policies.append(_policy_from_reflection(reflection))

        if changed:
            _promote_and_deprecate_policies(policies, self.promotion_threshold, self.min_promoted_confidence)
            self.write_all(policies)

        return policies

    def search(
        self,
        job_title: str,
        experience: str = "",
        education: str = "",
        limit: int = 5,
    ) -> List[PolicyItem]:
        profile_tokens = _profile_tokens(job_title, experience, education)
        scored: List[tuple[int, str, PolicyItem]] = []
        for policy in self.read_all():
            if policy.status != "promoted":
                continue

            score = 0
            policy_tokens = _profile_tokens(policy.job_title, policy.experience, policy.education)
            if _normalize_key(policy.scope) == "global":
                score += 2
            if _normalize_key(job_title) and _normalize_key(job_title) == _normalize_key(policy.job_title):
                score += 8
            elif profile_tokens & policy_tokens:
                score += 4
            if _normalize_key(experience) and _normalize_key(experience) == _normalize_key(policy.experience):
                score += 3
            if _normalize_key(education) and _normalize_key(education) == _normalize_key(policy.education):
                score += 1
            score += min(policy.evidence_count, 5)

            if score > 0:
                scored.append((score, policy.updated_at, policy))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [policy for _, _, policy in scored[:limit]]

    def _find_matching_policy(self, policies: List[PolicyItem], reflection: ReflectionItem) -> Optional[PolicyItem]:
        candidates = [
            policy
            for policy in policies
            if policy.status != "deprecated"
            and _same_policy_scope(policy, reflection)
        ]
        if not candidates:
            return None

        best_policy = max(
            candidates,
            key=lambda policy: _text_similarity(policy.policy, reflection.prompt_hint),
        )
        if _text_similarity(best_policy.policy, reflection.prompt_hint) >= 0.42:
            return best_policy
        return None


class ReflectionService:
    def __init__(self, store: Optional[ReflectionStore] = None, policy_store: Optional[PolicyStore] = None):
        self.store = store or ReflectionStore()
        self.policy_store = policy_store or PolicyStore()

    def get_prompt_guidelines(
        self,
        job_title: str,
        experience: str = "",
        education: str = "",
        limit: int = 5,
    ) -> str:
        policies = self.policy_store.search(
            job_title=job_title,
            experience=experience,
            education=education,
            limit=3,
        )
        reflections = self.store.search(
            job_title=job_title,
            experience=experience,
            education=education,
            limit=limit + len(policies),
        )
        policy_keys = {_normalize_key(policy.policy) for policy in policies}
        reflections = [
            reflection
            for reflection in reflections
            if _normalize_key(reflection.prompt_hint) not in policy_keys
        ][:max(limit - len(policies), 0)]
        return format_reflection_guidelines(reflections, policies)

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

        self.policy_store.consolidate(self.store.read_all())
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


def format_reflection_guidelines(
    reflections: List[ReflectionItem],
    policies: Optional[List[PolicyItem]] = None,
) -> str:
    policies = policies or []
    if not reflections and not policies:
        return ""

    sections = []
    policy_bullets = _unique_bullets(policy.policy for policy in policies)
    if policy_bullets:
        sections.append("# 승격된 면접 운영 정책\n" + "\n".join(policy_bullets))

    reflection_bullets = _unique_bullets(reflection.prompt_hint for reflection in reflections)
    if reflection_bullets:
        sections.append("# 최근 유사 면접에서 학습한 보정 지침\n" + "\n".join(reflection_bullets))

    if not sections:
        return ""

    return "\n" + "\n\n".join(sections)


def _unique_bullets(values: Iterable[str]) -> List[str]:
    bullets = []
    seen: set[str] = set()
    for value in values:
        hint = _compact_prompt_hint(value)
        normalized = _normalize_key(hint)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        bullets.append(f"- {hint}")
    return bullets


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


def _policy_from_reflection(reflection: ReflectionItem) -> PolicyItem:
    now = datetime.now(timezone.utc).isoformat()
    return PolicyItem(
        id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        status="candidate",
        scope=_policy_scope(reflection),
        job_title=reflection.job_title,
        experience=reflection.experience,
        education=reflection.education,
        policy=_compact_prompt_hint(reflection.prompt_hint),
        evidence_count=1,
        confidence=reflection.confidence,
        source_reflection_ids=[reflection.id],
        reason="created_from_reflection",
    )


def _merge_reflection_into_policy(policy: PolicyItem, reflection: ReflectionItem) -> None:
    if reflection.id not in policy.source_reflection_ids:
        previous_evidence = max(policy.evidence_count, 1)
        policy.source_reflection_ids.append(reflection.id)
        policy.evidence_count = len(policy.source_reflection_ids)
        policy.confidence = round(
            ((policy.confidence * previous_evidence) + reflection.confidence)
            / (previous_evidence + 1),
            2,
        )

    if _is_more_specific(reflection.prompt_hint, policy.policy):
        policy.policy = _compact_prompt_hint(reflection.prompt_hint)
        policy.reason = "updated_with_more_specific_reflection"

    policy.updated_at = datetime.now(timezone.utc).isoformat()


def _promote_and_deprecate_policies(
    policies: List[PolicyItem],
    promotion_threshold: int,
    min_promoted_confidence: float,
) -> None:
    for policy in policies:
        if policy.status == "deprecated":
            continue
        if policy.evidence_count >= promotion_threshold and policy.confidence >= min_promoted_confidence:
            policy.status = "promoted"
            policy.reason = "promoted_by_repeated_evidence"

    promoted = [policy for policy in policies if policy.status == "promoted"]
    for older in promoted:
        for newer in promoted:
            if older.id == newer.id or older.status == "deprecated":
                continue
            if not _same_policy_scope(older, newer):
                continue
            if _text_similarity(older.policy, newer.policy) < 0.62:
                continue
            if _is_better_policy(newer, older):
                older.status = "deprecated"
                older.replaced_by = newer.id
                older.reason = "superseded_by_better_policy"
                newer.supersedes = sorted(set(newer.supersedes + [older.id]))


def _policy_scope(reflection: ReflectionItem) -> str:
    if _normalize_key(reflection.job_title) and _normalize_key(reflection.experience):
        return "role_experience"
    if _normalize_key(reflection.job_title):
        return "role"
    return "global"


def _same_policy_scope(policy: PolicyItem, other: ReflectionItem | PolicyItem) -> bool:
    return (
        _normalize_key(policy.scope) == _normalize_key(getattr(other, "scope", _policy_scope(other)))
        and _normalize_key(policy.job_title) == _normalize_key(other.job_title)
        and _normalize_key(policy.experience) == _normalize_key(other.experience)
    )


def _text_similarity(left: str, right: str) -> float:
    left_tokens = _profile_tokens(left)
    right_tokens = _profile_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _is_more_specific(candidate: str, current: str) -> bool:
    candidate_tokens = _profile_tokens(candidate)
    current_tokens = _profile_tokens(current)
    return len(candidate_tokens) >= len(current_tokens) + 3


def _is_better_policy(candidate: PolicyItem, current: PolicyItem) -> bool:
    if candidate.evidence_count >= current.evidence_count + 2:
        return True
    if candidate.confidence >= current.confidence + 0.1 and _is_more_specific(candidate.policy, current.policy):
        return True
    return False
