#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.invite_service import InviteCodeStore, generate_invite_code, normalize_invite_code  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Create plaintext one-time TechTree invite codes in MongoDB.")
    parser.add_argument("--code", help="Invite code to store. If omitted, random codes are generated.")
    parser.add_argument("--count", type=int, default=None, help="Number of random codes to create. Defaults to 50 when --code is omitted.")
    parser.add_argument("--name", default="", help="Optional admin memo/name for every generated code.")
    parser.add_argument("--use-max", type=int, default=1, help="Max uses per code. Defaults to 1.")
    parser.add_argument("--status", default="active", choices=["active", "disabled"], help="Invite status.")
    args = parser.parse_args()

    count = 1 if args.code else (args.count or 50)
    store = InviteCodeStore()
    documents = []
    seen_codes = set()
    for _ in range(count):
        code = normalize_invite_code(args.code or generate_invite_code())
        while code in seen_codes:
            code = normalize_invite_code(generate_invite_code())
        seen_codes.add(code)
        documents.append(
            store.upsert_code(
                code=code,
                name=args.name,
                use_max=args.use_max,
                status_value=args.status,
            )
        )

    print(
        json.dumps(
            [
                {
                    "code": document["code"],
                    "name": document.get("name", ""),
                    "status": document.get("status", ""),
                    "use_max": document.get("use_max", 1),
                    "use_count": document.get("use_count", 0),
                }
                for document in documents
            ],
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
