from pathlib import Path
import json
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.reflection_mongo_store import ReflectionMongoClient


def main() -> None:
    client = ReflectionMongoClient()
    created = client.ensure_vector_search_indexes()
    print(f"Reflection database: {client.db.name}")
    print("Collections: interview_reflections, interview_policies")
    print(f"Vector search index creation attempted: {created}")
    print("Vector index definition:")
    print(json.dumps(client.build_vector_index_definition(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
