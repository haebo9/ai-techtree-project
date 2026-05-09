from langchain_core.messages import AIMessage, HumanMessage

from app.services.reflection_service import (
    ReflectionCandidate,
    ReflectionItem,
    ReflectionService,
    ReflectionStore,
    format_reflection_guidelines,
    safe_generate_and_store_reflections,
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


def test_format_reflection_guidelines_returns_prompt_section():
    guidelines = format_reflection_guidelines([_reflection()])

    assert "# 이전 면접에서 학습한 운영 지침" in guidelines
    assert "신입 지원자에게는" in guidelines


def test_service_stores_generated_reflections_without_transcript(monkeypatch, tmp_path):
    store = ReflectionStore(tmp_path / "reflections.jsonl")
    service = ReflectionService(store)

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
    )

    saved = store.read_all()
    assert stored_count == 1
    assert saved[0].prompt_hint.startswith("면접 초반에는")
    assert "Playwright" not in saved[0].model_dump_json(ensure_ascii=False)
    assert "test@example.com" not in saved[0].model_dump_json(ensure_ascii=False)
    assert "010-1234-5678" not in saved[0].model_dump_json(ensure_ascii=False)


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
