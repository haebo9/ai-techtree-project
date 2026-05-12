import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_openai import OpenAIEmbeddings
from pymongo import MongoClient, ReplaceOne
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


REFLECTION_COLLECTION = "interview_reflections"
POLICY_COLLECTION = "interview_policies"
VECTOR_FIELD = "embedding"


class MongoReflectionUnavailable(RuntimeError):
    pass


class ReflectionMongoClient:
    def __init__(
        self,
        mongo_url: Optional[str] = None,
        db_name: Optional[str] = None,
        *,
        server_selection_timeout_ms: int = 1500,
    ):
        self.mongo_url = mongo_url or settings.MONGODB_URL
        if not self.mongo_url:
            raise MongoReflectionUnavailable("MONGODB_URL is not configured")

        self.client = MongoClient(
            self.mongo_url,
            serverSelectionTimeoutMS=server_selection_timeout_ms,
            connectTimeoutMS=server_selection_timeout_ms,
        )
        self.db = self.client[db_name or settings.REFLECTION_DB_NAME]
        self.reflections = self.db[REFLECTION_COLLECTION]
        self.policies = self.db[POLICY_COLLECTION]
        self._embedder: Optional[OpenAIEmbeddings] = None
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        self.reflections.create_index("id", unique=True)
        self.reflections.create_index([("source_session_id", 1), ("prompt_hint_key", 1)], unique=True)
        self.reflections.create_index([("interview_mode_key", 1), ("job_title_key", 1), ("experience_key", 1), ("education_key", 1)])
        self.reflections.create_index([("confidence", -1), ("created_at", -1)])

        self.policies.create_index("id", unique=True)
        self.policies.create_index([("status", 1), ("interview_mode_key", 1), ("job_title_key", 1), ("experience_key", 1), ("education_key", 1)])
        self.policies.create_index([("status", 1), ("confidence", -1), ("evidence_count", -1)])

    def build_vector_index_definition(self) -> Dict[str, Any]:
        return {
            "name": settings.REFLECTION_VECTOR_INDEX_NAME,
            "type": "vectorSearch",
            "definition": {
                "fields": [
                    {
                        "type": "vector",
                        "path": VECTOR_FIELD,
                        "numDimensions": 1536,
                        "similarity": "cosine",
                    },
                    {"type": "filter", "path": "kind"},
                    {"type": "filter", "path": "status"},
                    {"type": "filter", "path": "job_title_key"},
                    {"type": "filter", "path": "experience_key"},
                    {"type": "filter", "path": "education_key"},
                    {"type": "filter", "path": "interview_mode_key"},
                ]
            },
        }

    def ensure_vector_search_indexes(self) -> bool:
        """
        Best-effort Atlas Vector Search index creation.

        Some local MongoDB servers and Atlas permissions do not support creating
        search indexes through the driver. In that case, return False and let the
        application keep using metadata search until the index is created in Atlas.
        """
        definition = self.build_vector_index_definition()
        created = False
        for collection in (self.reflections, self.policies):
            try:
                collection.create_search_index(definition)
                created = True
            except Exception as exc:
                logger.info("Vector index creation skipped for %s: %s", collection.name, exc)
        return created

    def upsert_reflection(self, reflection: Any) -> bool:
        document = _reflection_document(reflection)
        if not document.get("prompt_hint_key"):
            return False

        try:
            existing = self.reflections.find_one(
                {
                    "source_session_id": document.get("source_session_id", ""),
                    "prompt_hint_key": document["prompt_hint_key"],
                },
                {"_id": 1},
            )
            if existing:
                return False

            self.reflections.insert_one(self._with_embedding(document))
            return True
        except PyMongoError as exc:
            logger.warning("Mongo reflection upsert failed: %s", exc)
            raise MongoReflectionUnavailable(str(exc)) from exc

    def read_reflections(self, item_model: Any) -> List[Any]:
        try:
            cursor = self.reflections.find({}, {"_id": 0, VECTOR_FIELD: 0, "embedding_text": 0, "embedding_model": 0})
            return [item_model(**doc) for doc in cursor]
        except PyMongoError as exc:
            logger.warning("Mongo reflection read failed: %s", exc)
            raise MongoReflectionUnavailable(str(exc)) from exc

    def write_policies(self, policies: List[Any]) -> None:
        operations = []
        for policy in policies:
            document = _policy_document(policy)
            operations.append(ReplaceOne({"id": document["id"]}, self._with_embedding(document), upsert=True))

        try:
            if operations:
                self.policies.bulk_write(operations, ordered=False)
        except PyMongoError as exc:
            logger.warning("Mongo policy write failed: %s", exc)
            raise MongoReflectionUnavailable(str(exc)) from exc

    def read_policies(self, item_model: Any) -> List[Any]:
        try:
            cursor = self.policies.find({}, {"_id": 0, VECTOR_FIELD: 0, "embedding_text": 0, "embedding_model": 0})
            return [item_model(**doc) for doc in cursor]
        except PyMongoError as exc:
            logger.warning("Mongo policy read failed: %s", exc)
            raise MongoReflectionUnavailable(str(exc)) from exc

    def search_reflections(
        self,
        item_model: Any,
        *,
        query_text: str,
        job_title: str,
        experience: str,
        education: str,
        interview_mode: str,
        limit: int,
    ) -> List[Any]:
        vector_results = self._vector_search(
            collection=self.reflections,
            item_model=item_model,
            query_text=query_text,
            kind="reflection",
            status_filter=None,
            interview_mode=interview_mode,
            limit=limit,
        )
        if vector_results:
            return vector_results

        filter_query = _profile_filter(job_title, experience, education)
        try:
            cursor = self.reflections.find(
                filter_query,
                {"_id": 0, VECTOR_FIELD: 0, "embedding_text": 0, "embedding_model": 0},
            ).sort([("confidence", -1), ("created_at", -1)]).limit(max(limit * 3, limit))
            docs = _rank_docs_by_mode(list(cursor), interview_mode)
            return [item_model(**doc) for doc in docs[:limit]]
        except PyMongoError as exc:
            logger.warning("Mongo reflection search failed: %s", exc)
            raise MongoReflectionUnavailable(str(exc)) from exc

    def search_policies(
        self,
        item_model: Any,
        *,
        query_text: str,
        job_title: str,
        experience: str,
        education: str,
        interview_mode: str,
        limit: int,
    ) -> List[Any]:
        vector_results = self._vector_search(
            collection=self.policies,
            item_model=item_model,
            query_text=query_text,
            kind="policy",
            status_filter="promoted",
            interview_mode=interview_mode,
            limit=limit,
        )
        if vector_results:
            return vector_results

        filter_query = {"status": "promoted", **_profile_filter(job_title, experience, education)}
        try:
            cursor = self.policies.find(
                filter_query,
                {"_id": 0, VECTOR_FIELD: 0, "embedding_text": 0, "embedding_model": 0},
            ).sort([("evidence_count", -1), ("confidence", -1), ("updated_at", -1)]).limit(max(limit * 3, limit))
            docs = _rank_docs_by_mode(list(cursor), interview_mode)
            return [item_model(**doc) for doc in docs[:limit]]
        except PyMongoError as exc:
            logger.warning("Mongo policy search failed: %s", exc)
            raise MongoReflectionUnavailable(str(exc)) from exc

    def _vector_search(
        self,
        *,
        collection: Collection,
        item_model: Any,
        query_text: str,
        kind: str,
        status_filter: Optional[str],
        interview_mode: str,
        limit: int,
    ) -> List[Any]:
        if not settings.REFLECTION_VECTOR_SEARCH_ENABLED:
            return []

        query_vector = self._embed_query(query_text)
        if not query_vector:
            return []

        filter_query: Dict[str, Any] = {"kind": kind}
        if status_filter:
            filter_query["status"] = status_filter

        pipeline = [
            {
                "$vectorSearch": {
                    "index": settings.REFLECTION_VECTOR_INDEX_NAME,
                    "path": VECTOR_FIELD,
                    "queryVector": query_vector,
                    "numCandidates": max(limit * 20, 50),
                    "limit": max(limit * 3, limit),
                    "filter": filter_query,
                }
            },
            {"$project": {"_id": 0, VECTOR_FIELD: 0, "embedding_text": 0, "embedding_model": 0}},
        ]

        try:
            docs = _rank_docs_by_mode(list(collection.aggregate(pipeline)), interview_mode)
            return [item_model(**doc) for doc in docs[:limit]]
        except PyMongoError as exc:
            logger.info("Vector search unavailable for %s: %s", collection.name, exc)
            return []

    def _with_embedding(self, document: Dict[str, Any]) -> Dict[str, Any]:
        embedding_text = document.get("embedding_text", "")
        if not settings.REFLECTION_VECTOR_SEARCH_ENABLED or not embedding_text:
            return document

        vector = self._embed_query(embedding_text)
        if vector:
            document[VECTOR_FIELD] = vector
            document["embedding_model"] = settings.REFLECTION_EMBEDDING_MODEL
        return document

    def _embed_query(self, text: str) -> List[float]:
        if not settings.OPENAI_API_KEY:
            return []

        if self._embedder is None:
            self._embedder = OpenAIEmbeddings(
                model=settings.REFLECTION_EMBEDDING_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
            )

        try:
            return self._embedder.embed_query(text)
        except Exception as exc:
            logger.info("Reflection embedding unavailable: %s", exc)
            return []


def _reflection_document(reflection: Any) -> Dict[str, Any]:
    doc = reflection.model_dump()
    doc["interview_mode"] = _normalize_interview_mode(doc.get("interview_mode"))
    doc.update({
        "kind": "reflection",
        "job_title_key": _normalize_key(doc.get("job_title", "")),
        "experience_key": _normalize_key(doc.get("experience", "")),
        "education_key": _normalize_key(doc.get("education", "")),
        "interview_mode_key": _normalize_interview_mode(doc.get("interview_mode")),
        "prompt_hint_key": _normalize_key(doc.get("prompt_hint", "")),
        "embedding_text": _reflection_embedding_text(doc),
        "synced_at": datetime.now(timezone.utc).isoformat(),
    })
    return doc


def _policy_document(policy: Any) -> Dict[str, Any]:
    doc = policy.model_dump()
    doc["interview_mode"] = _normalize_interview_mode(doc.get("interview_mode"))
    doc.update({
        "kind": "policy",
        "job_title_key": _normalize_key(doc.get("job_title", "")),
        "experience_key": _normalize_key(doc.get("experience", "")),
        "education_key": _normalize_key(doc.get("education", "")),
        "interview_mode_key": _normalize_interview_mode(doc.get("interview_mode")),
        "policy_key": _normalize_key(doc.get("policy", "")),
        "embedding_text": _policy_embedding_text(doc),
        "synced_at": datetime.now(timezone.utc).isoformat(),
    })
    return doc


def _reflection_embedding_text(doc: Dict[str, Any]) -> str:
    return "\n".join([
        f"면접 모드: {_normalize_interview_mode(doc.get('interview_mode'))}",
        f"직무: {doc.get('job_title', '')}",
        f"경력: {doc.get('experience', '')}",
        f"학력: {doc.get('education', '')}",
        f"태그: {', '.join(doc.get('tags', []))}",
        f"문제: {doc.get('issue', '')}",
        f"교훈: {doc.get('lesson', '')}",
        f"지침: {doc.get('prompt_hint', '')}",
    ]).strip()


def _policy_embedding_text(doc: Dict[str, Any]) -> str:
    return "\n".join([
        f"면접 모드: {_normalize_interview_mode(doc.get('interview_mode'))}",
        f"상태: {doc.get('status', '')}",
        f"범위: {doc.get('scope', '')}",
        f"직무: {doc.get('job_title', '')}",
        f"경력: {doc.get('experience', '')}",
        f"학력: {doc.get('education', '')}",
        f"근거 수: {doc.get('evidence_count', '')}",
        f"정책: {doc.get('policy', '')}",
    ]).strip()


def _profile_filter(job_title: str, experience: str, education: str) -> Dict[str, Any]:
    clauses = []
    job_key = _normalize_key(job_title)
    experience_key = _normalize_key(experience)
    education_key = _normalize_key(education)
    if job_key:
        clauses.append({"job_title_key": job_key})
    if experience_key:
        clauses.append({"experience_key": experience_key})
    if education_key:
        clauses.append({"education_key": education_key})
    return {"$or": clauses} if clauses else {}


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _normalize_interview_mode(value: Any) -> str:
    return "short" if _normalize_key(str(value or "")) == "short" else "long"


def _mode_score(item_mode: Any, requested_mode: str) -> int:
    item_mode = _normalize_interview_mode(item_mode)
    requested_mode = _normalize_interview_mode(requested_mode)
    if item_mode == requested_mode:
        return 5
    if item_mode == "long":
        return 1
    return 0


def _rank_docs_by_mode(docs: List[Dict[str, Any]], interview_mode: str) -> List[Dict[str, Any]]:
    return sorted(
        docs,
        key=lambda doc: (
            _mode_score(doc.get("interview_mode") or doc.get("interview_mode_key"), interview_mode),
            doc.get("evidence_count", 0),
            doc.get("confidence", 0),
            doc.get("updated_at") or doc.get("created_at") or "",
        ),
        reverse=True,
    )
