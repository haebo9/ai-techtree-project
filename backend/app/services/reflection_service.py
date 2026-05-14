import json
import os
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
from app.engine.prompts.reflection_analyzer import REFLECTION_ANALYZER_SYSTEM_PROMPT
from app.services.reflection_mongo_store import MongoReflectionUnavailable, ReflectionMongoClient

logger = get_logger(__name__)
_LOCAL_MEMORY_SYNCED_TO_MONGO = False
MODE_SCOPES = {"common", "short", "long"}
GOOD_OUTCOME_SCORE_THRESHOLD = 80
DEPRECATE_INJECTED_COUNT_THRESHOLD = 3
DEPRECATE_NEGATIVE_OUTCOME_THRESHOLD = 2
SHORT_ONLY_GUIDELINE_PATTERNS = (
    "짧은 면접",
    "7분",
    "1회 이하",
    "전체 1회",
    "최대 1회",
    "대표 경험 1개",
    "대표 경험은 1개",
    "빠른 면접",
)


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


def _normalize_interview_mode(value: str | None) -> str:
    normalized = _normalize_key(value or "")
    return "short" if normalized == "short" else "long"


def _normalize_mode_scope(value: str | None, fallback_mode: str = "long") -> str:
    normalized = _normalize_key(value or "")
    if normalized in MODE_SCOPES:
        return normalized
    return _normalize_interview_mode(fallback_mode)


def _mode_scope_allows(mode_scope: str | None, interview_mode: str) -> bool:
    normalized_scope = _normalize_mode_scope(mode_scope, interview_mode)
    normalized_mode = _normalize_interview_mode(interview_mode)
    return normalized_scope == "common" or normalized_scope == normalized_mode


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
    interview_mode: str = "long"
    mode_scope: str = "long"
    injected_count: int = 0
    last_injected_at: Optional[str] = None
    positive_outcome_count: int = 0
    negative_outcome_count: int = 0
    last_outcome_at: Optional[str] = None


class ReflectionCandidate(BaseModel):
    tags: List[str] = Field(default_factory=list)
    issue: str = Field(default="", description="이번 면접에서 관찰된 면접 운영상의 문제")
    lesson: str = Field(default="", description="다음 면접에 재사용할 수 있는 학습 내용")
    prompt_hint: str = Field(default="", description="면접관 시스템 프롬프트에 넣을 짧은 운영 지침")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    mode_scope: str = Field(
        default="",
        description="이 지침의 주입 범위. common, short, long 중 하나",
    )


class ReflectionGeneration(BaseModel):
    reflections: List[ReflectionCandidate] = Field(default_factory=list)


class PromptGuidelineSelection(BaseModel):
    text: str = ""
    reflection_ids: List[str] = Field(default_factory=list)
    policy_ids: List[str] = Field(default_factory=list)


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
    interview_mode: str = "long"
    mode_scope: str = "long"
    injected_count: int = 0
    last_injected_at: Optional[str] = None
    positive_outcome_count: int = 0
    negative_outcome_count: int = 0
    last_outcome_at: Optional[str] = None
    deprecated_at: Optional[str] = None


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
        if _contains_transcript_artifact(item.prompt_hint, item.issue, item.lesson):
            logger.warning("Skipping reflection that appears to contain raw transcript text")
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

    def write_all(self, reflections: List[ReflectionItem]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            for reflection in reflections:
                file.write(reflection.model_dump_json(ensure_ascii=False) + "\n")

    def search(
        self,
        job_title: str,
        experience: str = "",
        education: str = "",
        interview_mode: str = "",
        limit: int = 5,
    ) -> List[ReflectionItem]:
        normalized_mode = _normalize_interview_mode(interview_mode)

        scored: List[tuple[int, str, ReflectionItem]] = []
        for reflection in self.read_all():
            if not _mode_scope_allows(reflection.mode_scope, normalized_mode):
                continue

            profile_score = _profile_match_score(
                reflection,
                job_title=job_title,
                experience=experience,
                education=education,
            )
            if profile_score <= 0:
                continue

            score = profile_score

            if reflection.confidence >= 0.7:
                score += 1

            score += _mode_scope_score(reflection.mode_scope, normalized_mode)
            score += min(reflection.positive_outcome_count, 3)
            score -= min(reflection.negative_outcome_count, 3)

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
        policies, changed = consolidate_policy_items(policies, reflections, self)

        if changed:
            self.write_all(policies)

        return policies

    def search(
        self,
        job_title: str,
        experience: str = "",
        education: str = "",
        interview_mode: str = "",
        limit: int = 5,
    ) -> List[PolicyItem]:
        normalized_mode = _normalize_interview_mode(interview_mode)
        scored: List[tuple[int, str, PolicyItem]] = []
        for policy in self.read_all():
            if policy.status != "promoted":
                continue
            if not _mode_scope_allows(policy.mode_scope, normalized_mode):
                continue

            profile_score = _profile_match_score(
                policy,
                job_title=job_title,
                experience=experience,
                education=education,
            )
            if profile_score <= 0:
                continue

            score = profile_score
            score += min(policy.evidence_count, 5)
            score += _mode_scope_score(policy.mode_scope, normalized_mode)
            score += min(policy.positive_outcome_count, 3)
            score -= min(policy.negative_outcome_count, 3)

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
        similarity = _text_similarity(best_policy.policy, reflection.prompt_hint)
        if _policy_merge_allowed(best_policy, reflection, similarity):
            return best_policy
        return None


def consolidate_policy_items(
    policies: List[PolicyItem],
    reflections: List[ReflectionItem],
    policy_store: PolicyStore,
) -> tuple[List[PolicyItem], bool]:
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
        matched_policy = policy_store._find_matching_policy(policies, reflection)
        if matched_policy:
            _merge_reflection_into_policy(matched_policy, reflection)
        else:
            policies.append(_policy_from_reflection(reflection))

    if changed:
        _promote_and_deprecate_policies(
            policies,
            policy_store.promotion_threshold,
            policy_store.min_promoted_confidence,
        )

    return policies, changed


class ReflectionService:
    def __init__(self, store: Optional[ReflectionStore] = None, policy_store: Optional[PolicyStore] = None):
        self.store = store or ReflectionStore()
        self.policy_store = policy_store or PolicyStore()
        self.mongo_client = _create_mongo_client_if_enabled() if store is None and policy_store is None else None
        self._sync_local_memory_to_mongo()

    def get_prompt_guidelines(
        self,
        job_title: str,
        experience: str = "",
        education: str = "",
        resume: str = "",
        job_context: str = "",
        interview_mode: str = "",
        limit: int = 5,
    ) -> str:
        return self.select_prompt_guidelines(
            job_title=job_title,
            experience=experience,
            education=education,
            resume=resume,
            job_context=job_context,
            interview_mode=interview_mode,
            limit=limit,
        ).text

    def select_prompt_guidelines(
        self,
        job_title: str,
        experience: str = "",
        education: str = "",
        resume: str = "",
        job_context: str = "",
        interview_mode: str = "",
        limit: int = 5,
    ) -> PromptGuidelineSelection:
        normalized_mode = _normalize_interview_mode(interview_mode)
        if self.mongo_client:
            try:
                query_text = _guideline_query_text(
                    job_title=job_title,
                    experience=experience,
                    education=education,
                    resume=resume,
                    job_context=job_context,
                    interview_mode=interview_mode,
                )
                policies = self.mongo_client.search_policies(
                    PolicyItem,
                    query_text=query_text,
                    job_title=job_title,
                    experience=experience,
                    education=education,
                    interview_mode=normalized_mode,
                    limit=3,
                )
                reflections = self.mongo_client.search_reflections(
                    ReflectionItem,
                    query_text=query_text,
                    job_title=job_title,
                    experience=experience,
                    education=education,
                    interview_mode=normalized_mode,
                    limit=limit + len(policies),
                )
                policies = _filter_guideline_items(
                    policies,
                    normalized_mode,
                    "policy",
                    job_title=job_title,
                    experience=experience,
                    education=education,
                    require_promoted=True,
                )
                reflections = _filter_guideline_items(
                    reflections,
                    normalized_mode,
                    "prompt_hint",
                    job_title=job_title,
                    experience=experience,
                    education=education,
                )
                policy_keys = {_normalize_key(policy.policy) for policy in policies}
                reflections = [
                    reflection
                    for reflection in reflections
                    if _normalize_key(reflection.prompt_hint) not in policy_keys
                ][:max(limit - len(policies), 0)]
                return PromptGuidelineSelection(
                    text=format_reflection_guidelines(reflections, policies),
                    reflection_ids=[reflection.id for reflection in reflections],
                    policy_ids=[policy.id for policy in policies],
                )
            except MongoReflectionUnavailable:
                logger.info("Falling back to local reflection guidelines")

        policies = self.policy_store.search(
            job_title=job_title,
            experience=experience,
            education=education,
            interview_mode=normalized_mode,
            limit=3,
        )
        reflections = self.store.search(
            job_title=job_title,
            experience=experience,
            education=education,
            interview_mode=normalized_mode,
            limit=limit + len(policies),
        )
        policies = _filter_guideline_items(
            policies,
            normalized_mode,
            "policy",
            job_title=job_title,
            experience=experience,
            education=education,
            require_promoted=True,
        )
        reflections = _filter_guideline_items(
            reflections,
            normalized_mode,
            "prompt_hint",
            job_title=job_title,
            experience=experience,
            education=education,
        )
        policy_keys = {_normalize_key(policy.policy) for policy in policies}
        reflections = [
            reflection
            for reflection in reflections
            if _normalize_key(reflection.prompt_hint) not in policy_keys
        ][:max(limit - len(policies), 0)]
        return PromptGuidelineSelection(
            text=format_reflection_guidelines(reflections, policies),
            reflection_ids=[reflection.id for reflection in reflections],
            policy_ids=[policy.id for policy in policies],
        )

    def generate_and_store(
        self,
        *,
        session_id: str,
        job_title: str,
        experience: str,
        education: str,
        messages: Iterable[Any],
        evaluation: Dict[str, Any],
        interview_mode: str = "long",
    ) -> int:
        normalized_mode = _normalize_interview_mode(interview_mode)
        candidates = self._generate_candidates(
            job_title=job_title,
            experience=experience,
            education=education,
            messages=messages,
            evaluation=evaluation,
            interview_mode=normalized_mode,
        )

        stored_count = 0
        stored_items: List[ReflectionItem] = []
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
                interview_mode=normalized_mode,
                mode_scope=_normalize_mode_scope(candidate.mode_scope, normalized_mode),
            )
            if self._append_reflection(item):
                stored_count += 1
                stored_items.append(item)

        self._consolidate_policies(stored_items)
        return stored_count

    def ensure_vector_search_indexes(self) -> bool:
        if not self.mongo_client:
            return False
        return self.mongo_client.ensure_vector_search_indexes()

    def _sync_local_memory_to_mongo(self) -> None:
        global _LOCAL_MEMORY_SYNCED_TO_MONGO
        if not self.mongo_client:
            return
        if _LOCAL_MEMORY_SYNCED_TO_MONGO:
            return

        try:
            for reflection in self.store.read_all():
                self.mongo_client.upsert_reflection(reflection)
            policies = self.policy_store.read_all()
            if policies:
                self.mongo_client.write_policies(policies)
            _LOCAL_MEMORY_SYNCED_TO_MONGO = True
        except MongoReflectionUnavailable:
            logger.info("Skipping local reflection memory sync because Mongo is unavailable")

    def _append_reflection(self, item: ReflectionItem) -> bool:
        stored_in_mongo = False
        if self.mongo_client:
            try:
                stored_in_mongo = self.mongo_client.upsert_reflection(item)
            except MongoReflectionUnavailable:
                logger.info("Falling back to local reflection store")

        stored_in_local = self.store.append(item)
        return stored_in_mongo or stored_in_local

    def _consolidate_policies(self, stored_items: List[ReflectionItem]) -> None:
        if not stored_items:
            return

        self.policy_store.consolidate(self.store.read_all())

        if self.mongo_client:
            try:
                reflections = self.mongo_client.read_reflections(ReflectionItem)
                policies = self.mongo_client.read_policies(PolicyItem)
                consolidated, changed = consolidate_policy_items(policies, reflections, self.policy_store)
                if changed:
                    self.mongo_client.write_policies(consolidated)
                return
            except MongoReflectionUnavailable:
                logger.info("Falling back to local policy store")

    def record_guideline_outcomes(
        self,
        *,
        source_reflection_ids: List[str],
        source_policy_ids: List[str],
        session_id: str,
        evaluation: Dict[str, Any],
    ) -> None:
        reflection_ids = {source_id for source_id in source_reflection_ids if source_id}
        policy_ids = {source_id for source_id in source_policy_ids if source_id}
        if not reflection_ids and not policy_ids:
            return

        timestamp = datetime.now(timezone.utc).isoformat()
        score = _evaluation_score(evaluation)
        local_reflections = self.store.read_all()
        local_policies = self.policy_store.read_all()
        new_reflections = [
            reflection
            for reflection in local_reflections
            if _normalize_key(reflection.source_session_id) == _normalize_key(session_id)
        ]

        reflections_changed = _record_reflection_outcomes(
            local_reflections,
            reflection_ids,
            new_reflections,
            score,
            timestamp,
        )
        policies_changed = _record_policy_outcomes(
            local_policies,
            policy_ids,
            new_reflections,
            score,
            timestamp,
        )

        if reflections_changed:
            self.store.write_all(local_reflections)
        if policies_changed:
            self.policy_store.write_all(local_policies)

        if self.mongo_client:
            try:
                mongo_reflections = self.mongo_client.read_reflections(ReflectionItem)
                mongo_policies = self.mongo_client.read_policies(PolicyItem)
                mongo_new_reflections = [
                    reflection
                    for reflection in mongo_reflections
                    if _normalize_key(reflection.source_session_id) == _normalize_key(session_id)
                ]
                if _record_reflection_outcomes(
                    mongo_reflections,
                    reflection_ids,
                    mongo_new_reflections,
                    score,
                    timestamp,
                ):
                    self.mongo_client.write_reflections(mongo_reflections)
                if _record_policy_outcomes(
                    mongo_policies,
                    policy_ids,
                    mongo_new_reflections,
                    score,
                    timestamp,
                ):
                    self.mongo_client.write_policies(mongo_policies)
            except MongoReflectionUnavailable:
                logger.info("Skipping Mongo guideline outcome update")

    def _generate_candidates(
        self,
        *,
        job_title: str,
        experience: str,
        education: str,
        messages: Iterable[Any],
        evaluation: Dict[str, Any],
        interview_mode: str = "long",
    ) -> List[ReflectionCandidate]:
        transcript = _format_messages(messages, max_chars=7000)
        if not transcript:
            return []

        evaluation_summary = json.dumps(evaluation, ensure_ascii=False, default=str)[:3500]

        user_prompt = f"""
[지원자 조건]
- 지원 직무: {job_title or "정보 없음"}
- 경력: {experience or "정보 없음"}
- 학력: {education or "정보 없음"}
- 면접 모드: {_normalize_interview_mode(interview_mode)}
- 지침 범위 판단: common, short, long 중 하나를 mode_scope로 지정

[면접 대화]
{transcript}

[평가 결과]
{evaluation_summary}
"""

        llm = get_llm(temperature=0.1)
        structured_llm = llm.with_structured_output(ReflectionGeneration)
        result = structured_llm.invoke([
            SystemMessage(content=REFLECTION_ANALYZER_SYSTEM_PROMPT),
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


def _filter_guideline_items(
    items: List[Any],
    interview_mode: str,
    text_field: str,
    *,
    job_title: str,
    experience: str,
    education: str,
    require_promoted: bool = False,
) -> List[Any]:
    normalized_mode = _normalize_interview_mode(interview_mode)
    filtered = []
    for item in items:
        if require_promoted and getattr(item, "status", "") != "promoted":
            continue
        if getattr(item, "status", "") == "deprecated":
            continue
        if not _mode_scope_allows(getattr(item, "mode_scope", ""), normalized_mode):
            continue
        if _profile_match_score(item, job_title=job_title, experience=experience, education=education) <= 0:
            continue
        text = str(getattr(item, text_field, "") or "")
        if normalized_mode == "long" and _is_short_only_guideline(text):
            continue
        filtered.append(item)
    return filtered


def _is_short_only_guideline(text: str) -> bool:
    normalized = _normalize_key(text)
    return any(_normalize_key(pattern) in normalized for pattern in SHORT_ONLY_GUIDELINE_PATTERNS)


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


def _record_reflection_outcomes(
    reflections: List[ReflectionItem],
    source_ids: set[str],
    new_reflections: List[ReflectionItem],
    score: Optional[float],
    timestamp: str,
) -> bool:
    changed = False
    for reflection in reflections:
        if reflection.id not in source_ids:
            continue
        repeated_issue = _guideline_issue_repeated(reflection.prompt_hint, new_reflections)
        reflection.injected_count += 1
        reflection.last_injected_at = timestamp
        if repeated_issue:
            reflection.negative_outcome_count += 1
            reflection.last_outcome_at = timestamp
        elif score is not None and score >= GOOD_OUTCOME_SCORE_THRESHOLD:
            reflection.positive_outcome_count += 1
            reflection.last_outcome_at = timestamp
        changed = True
    return changed


def _record_policy_outcomes(
    policies: List[PolicyItem],
    source_ids: set[str],
    new_reflections: List[ReflectionItem],
    score: Optional[float],
    timestamp: str,
) -> bool:
    changed = False
    for policy in policies:
        if policy.id not in source_ids:
            continue
        repeated_issue = _guideline_issue_repeated(policy.policy, new_reflections)
        policy.injected_count += 1
        policy.last_injected_at = timestamp
        if repeated_issue:
            policy.negative_outcome_count += 1
            policy.last_outcome_at = timestamp
        elif score is not None and score >= GOOD_OUTCOME_SCORE_THRESHOLD:
            policy.positive_outcome_count += 1
            policy.last_outcome_at = timestamp

        if (
            policy.status != "deprecated"
            and policy.injected_count >= DEPRECATE_INJECTED_COUNT_THRESHOLD
            and policy.negative_outcome_count >= DEPRECATE_NEGATIVE_OUTCOME_THRESHOLD
        ):
            policy.status = "deprecated"
            policy.reason = "deprecated_by_repeated_negative_outcomes"
            policy.deprecated_at = timestamp
        policy.updated_at = timestamp
        changed = True
    return changed


def _guideline_issue_repeated(guideline_text: str, new_reflections: List[ReflectionItem]) -> bool:
    guideline = _normalize_key(guideline_text)
    if not guideline or not new_reflections:
        return False
    for reflection in new_reflections:
        candidate_text = " ".join([
            reflection.issue,
            reflection.lesson,
            reflection.prompt_hint,
            " ".join(reflection.tags),
        ])
        if _text_similarity(guideline, candidate_text) >= 0.32:
            return True
    return False


def _evaluation_score(evaluation: Dict[str, Any]) -> Optional[float]:
    raw_score = evaluation.get("score")
    if isinstance(raw_score, dict):
        raw_score = raw_score.get("value") or raw_score.get("score")
    try:
        if raw_score is None:
            return None
        return float(raw_score)
    except (TypeError, ValueError):
        return None


def safe_generate_and_store_reflections(
    *,
    session_id: str,
    job_title: str,
    experience: str,
    education: str,
    messages: Iterable[Any],
    evaluation: Dict[str, Any],

    interview_mode: str = "long",
    injected_reflection_ids: Optional[List[str]] = None,
    injected_policy_ids: Optional[List[str]] = None,
) -> int:
    service = ReflectionService()
    stored_count = 0
    try:
        stored_count = service.generate_and_store(
            session_id=session_id,
            job_title=job_title,
            experience=experience,
            education=education,
            messages=messages,
            evaluation=evaluation,

            interview_mode=interview_mode,
        )
    except Exception as exc:
        logger.warning("Reflection generation failed for session %s: %s", session_id, exc)

    try:
        service.record_guideline_outcomes(
            source_reflection_ids=injected_reflection_ids or [],
            source_policy_ids=injected_policy_ids or [],
            session_id=session_id,
            evaluation=evaluation,
        )
    except Exception as exc:
        logger.warning("Reflection guideline outcome recording failed for session %s: %s", session_id, exc)

    return stored_count


def reset_reflection_memory() -> Dict[str, Any]:
    """Delete local and Mongo reflection memory without creating an archive."""
    global _LOCAL_MEMORY_SYNCED_TO_MONGO
    reflection_path = _default_reflection_store_path()
    policy_path = _default_policy_store_path()
    reflection_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    reflection_path.write_text("", encoding="utf-8")
    policy_path.write_text("", encoding="utf-8")
    result: Dict[str, Any] = {
        "jsonl_reflections_cleared": True,
        "jsonl_policies_cleared": True,
        "mongo_reflections_deleted": None,
        "mongo_policies_deleted": None,
    }

    if settings.MONGODB_URL:
        try:
            mongo_client = ReflectionMongoClient()
            deleted = mongo_client.reset_memory()
            result.update(deleted)
        except Exception as exc:
            result["mongo_error"] = str(exc)
            logger.warning("Mongo reflection memory reset failed: %s", exc)

    _LOCAL_MEMORY_SYNCED_TO_MONGO = False
    return result


def _create_mongo_client_if_enabled() -> Optional[ReflectionMongoClient]:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return None

    backend = _normalize_key(settings.REFLECTION_STORAGE_BACKEND)
    if backend == "jsonl":
        return None
    if not settings.MONGODB_URL:
        if backend == "mongo":
            logger.warning("REFLECTION_STORAGE_BACKEND=mongo but MONGODB_URL is not configured")
        return None

    try:
        return ReflectionMongoClient()
    except Exception as exc:
        if backend == "mongo":
            logger.warning("Mongo reflection storage unavailable: %s", exc)
        else:
            logger.info("Mongo reflection storage unavailable; using JSONL fallback: %s", exc)
        return None


def _guideline_query_text(
    *,
    job_title: str,
    experience: str,
    education: str,
    resume: str = "",
    job_context: str = "",
    interview_mode: str = "",
) -> str:
    return "\n".join([
        f"지원 직무: {job_title or '정보 없음'}",
        f"경력 조건: {experience or '정보 없음'}",
        f"학력 조건: {education or '정보 없음'}",
        f"면접 모드: {interview_mode or '정보 없음'}",
        f"이력 요약 힌트: {_short_context(resume)}",
        f"채용 공고 힌트: {_short_context(job_context)}",
        "다음 면접에서 재사용할 면접관 운영 지침을 찾는다.",
    ])


def _short_context(value: str, limit: int = 800) -> str:
    text = re.sub(r"\s+", " ", (value or "").strip())
    if not text:
        return "정보 없음"
    return text[:limit]


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


def _contains_transcript_artifact(*values: str) -> bool:
    text = "\n".join(value or "" for value in values)
    if re.search(r"(지원자|면접관)\s*:", text):
        return True
    if re.search(r"(?i)\b(user|assistant|ai|human)\s*:", text):
        return True
    if "라고 말" in text or "라고 답" in text:
        return True
    return False


def _profile_match_score(item: Any, *, job_title: str, experience: str, education: str) -> int:
    requested_job_title = _normalize_key(job_title)
    requested_experience = _normalize_key(experience)
    requested_education = _normalize_key(education)
    item_job_title = _normalize_key(getattr(item, "job_title", ""))
    item_experience = _normalize_key(getattr(item, "experience", ""))
    item_education = _normalize_key(getattr(item, "education", ""))

    score = 0
    if _normalize_key(getattr(item, "scope", "")) == "global":
        score += 2

    if requested_job_title and item_job_title:
        if requested_job_title == item_job_title:
            score += 8
        elif requested_job_title in item_job_title or item_job_title in requested_job_title:
            score += 6
        else:
            requested_tokens = _profile_tokens(job_title)
            item_tokens = _profile_tokens(item_job_title, " ".join(getattr(item, "tags", []) or []))
            if len(requested_tokens & item_tokens) >= 2:
                score += 4
            else:
                return 0

    if requested_experience and item_experience:
        if requested_experience == item_experience:
            score += 3
        elif requested_experience in item_experience or item_experience in requested_experience:
            score += 2

    if requested_education and item_education:
        if requested_education == item_education:
            score += 1

    return score


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
        interview_mode=_normalize_interview_mode(reflection.interview_mode),
        mode_scope=_normalize_mode_scope(reflection.mode_scope, reflection.interview_mode),
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

    policy.mode_scope = _merged_mode_scope(policy.mode_scope, reflection.mode_scope, reflection.interview_mode)

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
        and _normalize_mode_scope(policy.mode_scope, policy.interview_mode)
        == _normalize_mode_scope(getattr(other, "mode_scope", ""), getattr(other, "interview_mode", "long"))
    )


def _mode_scope_score(mode_scope: str, requested_mode: str) -> int:
    scope = _normalize_mode_scope(mode_scope, requested_mode)
    requested_mode = _normalize_interview_mode(requested_mode)
    if scope == requested_mode:
        return 5
    if scope == "common":
        return 3
    return 0


def _merged_mode_scope(current_scope: str, new_scope: str, new_mode: str) -> str:
    current = _normalize_mode_scope(current_scope, new_mode)
    new = _normalize_mode_scope(new_scope, new_mode)
    if current == new:
        return current
    return "common"


def _policy_merge_allowed(policy: PolicyItem, reflection: ReflectionItem, similarity: float) -> bool:
    policy_scope = _normalize_mode_scope(policy.mode_scope, policy.interview_mode)
    reflection_scope = _normalize_mode_scope(reflection.mode_scope, reflection.interview_mode)
    if policy_scope == reflection_scope:
        return similarity >= 0.42
    if "common" in (policy_scope, reflection_scope):
        return similarity >= 0.6 and not _is_mode_specific_text(policy.policy, reflection.prompt_hint)
    return False


def _is_mode_specific_text(*values: str) -> bool:
    text = _normalize_key(" ".join(values))
    return any(keyword in text for keyword in (
        "짧은",
        "긴",
        "빠른",
        "실전",
        "7분",
        "20분",
        "꼬리 질문",
        "꼬리질문",
        "마무리",
        "종료 멘트",
    ))


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
