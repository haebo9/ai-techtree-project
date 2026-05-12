from langchain_core.messages import AIMessage, HumanMessage

from app.services.reflection_service import (
    PolicyItem,
    PolicyStore,
    ReflectionCandidate,
    ReflectionItem,
    ReflectionService,
    ReflectionStore,
    consolidate_policy_items,
    format_reflection_guidelines,
    safe_generate_and_store_reflections,
    _guideline_query_text,
)
from app.services.reflection_mongo_store import (
    ReflectionMongoClient,
    _policy_document,
    _reflection_document,
)


def _reflection(**overrides):
    data = {
        "id": "reflection-1",
        "created_at": "2026-05-10T00:00:00+00:00",
        "job_title": "QA Engineer",
        "experience": "신입",
        "education": "학사",
        "tags": ["qa", "entry"],
        "issue": "공고 요건 확인이 늦음",
        "lesson": "신입 지원자에게 경력 질문을 오래 끌지 않는다.",
        "prompt_hint": "신입 지원자에게는 경력 연차 검증보다 기초 역량과 성장 가능성을 먼저 확인하세요.",
        "confidence": 0.82,
        "source_session_id": "session-1",
    }
    data.update(overrides)
    return ReflectionItem(**data)


def test_reflection_store_appends_and_reads(tmp_path):
    store = ReflectionStore(tmp_path / "reflections.jsonl")
    item = _reflection()

    assert store.append(item)
    assert store.read_all() == [item]


def test_legacy_reflection_defaults_to_long_mode(tmp_path):
    path = tmp_path / "reflections.jsonl"
    path.write_text(
        '{"id":"legacy","created_at":"2026-05-10T00:00:00+00:00","job_title":"QA Engineer","experience":"신입","education":"학사","tags":["qa"],"issue":"이슈","lesson":"교훈","prompt_hint":"질문을 명확히 하세요.","confidence":0.8,"source_session_id":"session-legacy"}\n',
        encoding="utf-8",
    )

    assert ReflectionStore(path).read_all()[0].interview_mode == "long"


def test_reflection_store_skips_corrupt_lines(tmp_path):
    path = tmp_path / "reflections.jsonl"
    path.write_text("{bad json}\n" + _reflection().model_dump_json(ensure_ascii=False) + "\n", encoding="utf-8")

    assert ReflectionStore(path).read_all() == [_reflection()]


def test_reflection_store_rejects_empty_and_duplicate_hints(tmp_path):
    store = ReflectionStore(tmp_path / "reflections.jsonl")

    assert not store.append(_reflection(prompt_hint="   "))
    assert store.append(_reflection(id="one"))
    assert not store.append(_reflection(id="two"))


def test_reflection_search_prioritizes_matching_profile(tmp_path):
    store = ReflectionStore(tmp_path / "reflections.jsonl")
    store.append(_reflection(id="qa-entry", job_title="QA Engineer", experience="신입", confidence=0.9))
    store.append(_reflection(
        id="backend-senior",
        job_title="Backend Engineer",
        experience="5년 이상",
        prompt_hint="경력직 백엔드 지원자에게는 시스템 설계 깊이를 먼저 검증하세요.",
    ))

    results = store.search("QA Engineer", experience="신입", education="학사", limit=1)

    assert [item.id for item in results] == ["qa-entry"]


def test_reflection_search_prioritizes_matching_interview_mode(tmp_path):
    store = ReflectionStore(tmp_path / "reflections.jsonl")
    store.append(_reflection(id="long", interview_mode="long", confidence=0.9, created_at="2026-05-10T00:00:00+00:00", source_session_id="long-session"))
    store.append(_reflection(id="short", interview_mode="short", confidence=0.9, created_at="2026-05-09T00:00:00+00:00", source_session_id="short-session"))

    short_results = store.search("QA Engineer", experience="신입", education="학사", interview_mode="short", limit=2)
    long_results = store.search("QA Engineer", experience="신입", education="학사", interview_mode="long", limit=2)

    assert [item.id for item in short_results] == ["short", "long"]
    assert [item.id for item in long_results] == ["long", "short"]


def test_policy_search_prioritizes_matching_interview_mode():
    short_policy = PolicyItem(
        id="short",
        created_at="2026-05-09T00:00:00+00:00",
        updated_at="2026-05-09T00:00:00+00:00",
        status="promoted",
        job_title="QA Engineer",
        experience="신입",
        education="학사",
        policy="짧은 면접에서는 꼬리 질문을 줄이세요.",
        evidence_count=3,
        confidence=0.8,
        interview_mode="short",
    )
    long_policy = PolicyItem(
        id="long",
        created_at="2026-05-10T00:00:00+00:00",
        updated_at="2026-05-10T00:00:00+00:00",
        status="promoted",
        job_title="QA Engineer",
        experience="신입",
        education="학사",
        policy="실전 면접에서는 답변 깊이를 충분히 검증하세요.",
        evidence_count=3,
        confidence=0.8,
        interview_mode="long",
    )
    policy_store = PolicyStore()
    policy_store.read_all = lambda: [long_policy, short_policy]

    results = policy_store.search("QA Engineer", experience="신입", education="학사", interview_mode="short", limit=2)

    assert [policy.id for policy in results] == ["short", "long"]


def test_format_reflection_guidelines_returns_prompt_section():
    guidelines = format_reflection_guidelines([_reflection()])

    assert "# 최근 유사 면접에서 학습한 보정 지침" in guidelines
    assert "신입 지원자에게는" in guidelines


def test_repeated_reflections_are_promoted_to_policy(tmp_path):
    reflection_store = ReflectionStore(tmp_path / "reflections.jsonl")
    policy_store = PolicyStore(tmp_path / "policies.jsonl")
    base_hint = "신입 QA 지원자에게는 리딩 경험보다 테스트 기초와 결함 재현 과정을 먼저 확인하세요."

    for index in range(3):
        reflection_store.append(_reflection(
            id=f"reflection-{index}",
            prompt_hint=base_hint,
            confidence=0.86,
            source_session_id=f"session-{index}",
        ))

    policies = policy_store.consolidate(reflection_store.read_all())

    promoted = [policy for policy in policies if policy.status == "promoted"]
    assert len(promoted) == 1
    assert promoted[0].evidence_count == 3
    assert promoted[0].policy == base_hint


def test_policy_consolidation_can_be_persisted_outside_jsonl():
    policy_store = PolicyStore()
    base_hint = "신입 QA 지원자에게는 테스트 기초와 결함 재현 과정을 우선 확인하세요."
    reflections = [
        _reflection(id=f"reflection-{index}", prompt_hint=base_hint, source_session_id=f"session-{index}", confidence=0.86)
        for index in range(3)
    ]

    policies, changed = consolidate_policy_items([], reflections, policy_store)

    promoted = [policy for policy in policies if policy.status == "promoted"]
    assert changed
    assert len(promoted) == 1
    assert promoted[0].evidence_count == 3


def test_prompt_guidelines_prioritize_promoted_policy(tmp_path):
    reflection_store = ReflectionStore(tmp_path / "reflections.jsonl")
    policy_store = PolicyStore(tmp_path / "policies.jsonl")
    policy_hint = "신입 QA 지원자에게는 테스트 기초와 결함 재현 과정을 우선 확인하세요."
    recent_hint = "면접 초반에는 공고의 필수 요건을 기준으로 첫 기술 질문을 구성하세요."

    for index in range(3):
        reflection_store.append(_reflection(
            id=f"policy-source-{index}",
            prompt_hint=policy_hint,
            confidence=0.88,
            source_session_id=f"session-{index}",
        ))
    reflection_store.append(_reflection(id="recent", prompt_hint=recent_hint, confidence=0.81, source_session_id="recent-session"))
    policy_store.consolidate(reflection_store.read_all())

    guidelines = ReflectionService(reflection_store, policy_store).get_prompt_guidelines(
        "QA Engineer",
        experience="신입",
        education="학사",
    )

    assert guidelines.index("# 승격된 면접 운영 정책") < guidelines.index("# 최근 유사 면접에서 학습한 보정 지침")
    assert policy_hint in guidelines
    assert recent_hint in guidelines


def test_service_stores_generated_reflections_without_transcript(monkeypatch, tmp_path):
    store = ReflectionStore(tmp_path / "reflections.jsonl")
    policy_store = PolicyStore(tmp_path / "policies.jsonl")
    service = ReflectionService(store, policy_store)

    monkeypatch.setattr(
        service,
        "_generate_candidates",
        lambda **_: [
            ReflectionCandidate(
                tags=["qa"],
                issue="질문이 공고 요건과 약하게 연결됨. test@example.com",
                lesson="공고의 필수 요건을 초반 질문에 반영한다.",
                prompt_hint="면접 초반에는 검색된 공고의 필수 요건을 기준으로 첫 기술 질문을 구성하세요. 010-1234-5678",
                confidence=0.9,
            )
        ],
    )

    stored_count = service.generate_and_store(
        session_id="session-1",
        job_title="QA Engineer",
        experience="신입",
        education="학사",
        messages=[
            AIMessage(content="테스트 자동화 경험을 설명해 주세요."),
            HumanMessage(content="개인 프로젝트에서 Playwright를 사용했습니다."),
        ],
        evaluation={"score": 75},
        saved_jobs=[{"title": "QA Engineer", "company": "A"}],
        interview_mode="short",
    )

    saved = store.read_all()
    assert stored_count == 1
    assert saved[0].interview_mode == "short"
    assert saved[0].prompt_hint.startswith("면접 초반에는")
    assert "Playwright" not in saved[0].model_dump_json(ensure_ascii=False)
    assert "test@example.com" not in saved[0].model_dump_json(ensure_ascii=False)
    assert "010-1234-5678" not in saved[0].model_dump_json(ensure_ascii=False)


def test_service_dual_writes_reflections_to_mongo_and_jsonl(monkeypatch, tmp_path):
    class FakeMongoClient:
        def __init__(self):
            self.reflections = []
            self.policies = []

        def upsert_reflection(self, item):
            self.reflections.append(item)
            return True

        def read_reflections(self, item_model):
            return self.reflections

        def read_policies(self, item_model):
            return self.policies

        def write_policies(self, policies):
            self.policies = policies

    store = ReflectionStore(tmp_path / "reflections.jsonl")
    policy_store = PolicyStore(tmp_path / "policies.jsonl")
    service = ReflectionService(store, policy_store)
    service.mongo_client = FakeMongoClient()

    monkeypatch.setattr(
        service,
        "_generate_candidates",
        lambda **_: [
            ReflectionCandidate(
                tags=["qa"],
                issue="질문이 공고 요건과 약하게 연결됨",
                lesson="공고의 필수 요건을 초반 질문에 반영한다.",
                prompt_hint="공고의 필수 요건을 기준으로 첫 기술 질문을 구성하세요.",
                confidence=0.9,
            )
        ],
    )

    stored_count = service.generate_and_store(
        session_id="session-1",
        job_title="QA Engineer",
        experience="신입",
        education="학사",
        messages=[AIMessage(content="질문"), HumanMessage(content="답변")],
        evaluation={"score": 75},
        saved_jobs=[],
    )

    assert stored_count == 1
    assert len(service.mongo_client.reflections) == 1
    assert len(store.read_all()) == 1


def test_service_dual_writes_policies_to_mongo_and_jsonl(monkeypatch, tmp_path):
    class FakeMongoClient:
        def __init__(self):
            self.reflections = []
            self.policies = []

        def upsert_reflection(self, item):
            self.reflections.append(item)
            return True

        def read_reflections(self, item_model):
            return self.reflections

        def read_policies(self, item_model):
            return self.policies

        def write_policies(self, policies):
            self.policies = policies

    store = ReflectionStore(tmp_path / "reflections.jsonl")
    policy_store = PolicyStore(tmp_path / "policies.jsonl")
    service = ReflectionService(store, policy_store)
    service.mongo_client = FakeMongoClient()
    base_hint = "신입 QA 지원자에게는 테스트 기초와 결함 재현 과정을 우선 확인하세요."

    for index in range(3):
        item = _reflection(
            id=f"reflection-{index}",
            prompt_hint=base_hint,
            source_session_id=f"session-{index}",
            confidence=0.9,
        )
        assert service._append_reflection(item)

    service._consolidate_policies(store.read_all())

    local_promoted = [policy for policy in policy_store.read_all() if policy.status == "promoted"]
    mongo_promoted = [policy for policy in service.mongo_client.policies if policy.status == "promoted"]
    assert len(local_promoted) == 1
    assert len(mongo_promoted) == 1


def test_reflection_store_rejects_raw_transcript_artifacts(tmp_path):
    store = ReflectionStore(tmp_path / "reflections.jsonl")

    assert not store.append(_reflection(
        id="raw-transcript",
        issue="지원자: 저는 Playwright를 사용했습니다.",
        lesson="지원자가 '저는 Playwright를 사용했습니다'라고 답했습니다.",
        prompt_hint="지원자: 저는 Playwright를 사용했습니다.",
    ))
    assert store.read_all() == []


def test_mongo_reflection_document_is_vector_ready_without_raw_transcript():
    document = _reflection_document(_reflection(
        issue="후속 질문이 직무 요건과 느슨하게 연결됨",
        lesson="공고 요건을 질문 축으로 사용한다.",
        prompt_hint="공고의 필수 요건을 기준으로 답변 검증 질문을 구성하세요.",
        interview_mode="short",
    ))

    assert document["kind"] == "reflection"
    assert document["interview_mode"] == "short"
    assert document["interview_mode_key"] == "short"
    assert document["job_title_key"] == "qa engineer"
    assert document["prompt_hint_key"]
    assert "embedding_text" in document
    assert "지원자:" not in document["embedding_text"]
    assert "면접관:" not in document["embedding_text"]


def test_guideline_query_text_uses_context_without_persisting_it():
    query = _guideline_query_text(
        job_title="AI Engineer",
        experience="신입",
        education="학사",
        resume="LangGraph 기반 실시간 면접 서비스 개발",
        job_context="AI Agent 및 LLM 서비스 운영 경험 우대",
        interview_mode="long",
    )

    assert "AI Engineer" in query
    assert "LangGraph" in query
    assert "LLM 서비스" in query
    assert "long" in query


def test_mongo_policy_document_excludes_deprecated_from_vector_filter_definition():
    policies, _ = consolidate_policy_items(
        [],
        [
            _reflection(id="a", source_session_id="a", confidence=0.9),
            _reflection(id="b", source_session_id="b", confidence=0.9),
            _reflection(id="c", source_session_id="c", confidence=0.9),
        ],
        PolicyStore(),
    )
    document = _policy_document(policies[0])
    definition = ReflectionMongoClient.__new__(ReflectionMongoClient).build_vector_index_definition()

    assert document["kind"] == "policy"
    assert document["embedding_text"]
    assert definition["name"]
    assert any(field["path"] == "interview_mode_key" for field in definition["definition"]["fields"])
    assert any(field["path"] == "status" for field in definition["definition"]["fields"])


def test_safe_generate_and_store_reflections_does_not_raise(monkeypatch):
    def raise_error(self, **kwargs):
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr(ReflectionService, "generate_and_store", raise_error)

    assert safe_generate_and_store_reflections(
        session_id="session-1",
        job_title="QA Engineer",
        experience="신입",
        education="학사",
        messages=[],
        evaluation={},
        saved_jobs=[],
    ) == 0
