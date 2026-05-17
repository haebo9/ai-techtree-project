import base64
import hashlib
import hmac
import json
import re
import secrets
import string
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request, Response, status
from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from app.core.config import settings
from app.core.logger import get_logger, send_telegram_message

logger = get_logger(__name__)

class InviteAuthError(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class InviteStoreUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class InviteSession:
    code: str
    name: str
    issued_at: int
    session_id: str


def normalize_invite_code(code: str) -> str:
    return re.sub(r"\s+", "", str(code or "")).upper()


def mask_invite_code(code: str) -> str:
    normalized = normalize_invite_code(code)
    if len(normalized) <= 6:
        return "*" * len(normalized)
    return f"{normalized[:3]}***{normalized[-3:]}"


def generate_invite_code(prefix: str = "TECHTREE") -> str:
    alphabet = "".join(ch for ch in string.ascii_uppercase + string.digits if ch not in "0O1I")
    suffix = "".join(secrets.choice(alphabet) for _ in range(7))
    return f"{prefix.upper()}-{suffix}"


def public_invite_info(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": document.get("status") or "",
        "use_count": int(document.get("use_count") or 0),
        "use_max": int(document.get("use_max") or 1),
    }


class InviteCodeStore:
    def __init__(self, mongo_url: str | None = None, db_name: str | None = None):
        self.mongo_url = mongo_url or settings.MONGODB_URL
        if not self.mongo_url:
            raise InviteStoreUnavailable("MONGODB_URL is not configured")

        self.client = MongoClient(
            self.mongo_url,
            serverSelectionTimeoutMS=1500,
            connectTimeoutMS=1500,
        )
        self.db = self.client[
            db_name
            or settings.INVITE_DB_NAME
            or settings.REFLECTION_DB_NAME
            or settings.DB_NAME
        ]
        self.collection: Collection = self.db[settings.INVITE_COLLECTION_NAME]

    def ensure_indexes(self) -> None:
        self.collection.create_index("code", unique=True)
        self.collection.create_index("status")

    def upsert_code(
        self,
        *,
        code: str,
        name: str = "",
        use_max: int = 1,
        status_value: str = "active",
    ) -> dict[str, Any]:
        self.ensure_indexes()
        normalized = normalize_invite_code(code)
        if not normalized:
            raise ValueError("invite code is empty")

        replacement = {
            "code": normalized,
            "name": name,
            "status": status_value,
            "use_max": max(1, int(use_max)),
            "use_count": 0,
        }
        return self.collection.find_one_and_replace(
            {"code": normalized},
            replacement,
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    def consume_code(self, code: str) -> dict[str, Any]:
        self.ensure_indexes()
        normalized = normalize_invite_code(code)
        if not normalized:
            raise InviteAuthError("empty_code")

        try:
            document = self.collection.find_one_and_update(
                {
                    "code": normalized,
                    "status": "active",
                    "$expr": {"$lt": [{"$ifNull": ["$use_count", 0]}, {"$ifNull": ["$use_max", 1]}]},
                },
                {
                    "$inc": {"use_count": 1},
                },
                return_document=ReturnDocument.AFTER,
            )
        except PyMongoError as exc:
            logger.error("Invite code lookup failed: %s", exc)
            raise InviteStoreUnavailable(str(exc)) from exc

        if document:
            return document

        existing = self.collection.find_one({"code": normalized}, {"status": 1, "use_count": 1, "use_max": 1})
        if not existing:
            raise InviteAuthError("not_found")
        if existing.get("status") != "active":
            raise InviteAuthError("inactive")
        raise InviteAuthError("usage_limit_reached")


def _session_secret() -> str:
    secret = settings.INVITE_SESSION_SECRET or settings.OPENAI_API_KEY
    if not secret:
        raise InviteStoreUnavailable("INVITE_SESSION_SECRET is not configured")
    return secret


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}")


def create_invite_session_token(document: dict[str, Any]) -> str:
    payload = {
        "sid": str(uuid.uuid4()),
        "code": normalize_invite_code(document.get("code") or ""),
        "name": document.get("name") or "",
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    encoded_payload = _b64_encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_session_secret().encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{signature}"


def parse_invite_session_token(token: str) -> InviteSession | None:
    try:
        encoded_payload, signature = token.split(".", 1)
        expected = hmac.new(_session_secret().encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_b64_decode(encoded_payload).decode("utf-8"))
        return InviteSession(
            code=normalize_invite_code(payload.get("code") or ""),
            name=str(payload.get("name") or ""),
            issued_at=int(payload.get("iat") or 0),
            session_id=str(payload.get("sid") or ""),
        )
    except Exception:
        return None


def set_invite_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.INVITE_SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def clear_invite_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.INVITE_SESSION_COOKIE_NAME,
        path="/",
        secure=settings.is_production,
        httponly=True,
        samesite="lax",
    )


def get_invite_session_from_request(request: Request) -> InviteSession | None:
    if not settings.INVITE_AUTH_ENABLED:
        return InviteSession(
            code="AUTH_DISABLED",
            name="",
            issued_at=0,
            session_id="disabled",
        )
    token = request.cookies.get(settings.INVITE_SESSION_COOKIE_NAME)
    if not token:
        return None
    return parse_invite_session_token(token)


def require_invite_session(request: Request) -> InviteSession:
    session = get_invite_session_from_request(request)
    if session:
        return session
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="초대코드 인증이 필요합니다.",
    )


def notify_invite_verified(document: dict[str, Any]) -> None:
    try:
        info = public_invite_info(document)
        usage = f"{info['use_count']}/{info['use_max']}"
        name = str(document.get("name") or "미입력")
        send_telegram_message(
            "\n".join(
                [
                    "✅ 초대코드 인증 성공",
                    f"- code: {normalize_invite_code(str(document.get('code') or ''))}",
                    f"- name: {name}",
                    f"- status: {info['status']}",
                    f"- usage: {usage}",
                ]
            )
        )
    except Exception as exc:
        logger.warning("Invite auth notification failed: %s", exc)
