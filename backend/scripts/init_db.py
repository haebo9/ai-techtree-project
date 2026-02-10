import sys
import os

# Backend root 경로를 path에 추가하여 app 모듈 import 가능하게 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.dirname(current_dir)
sys.path.append(backend_root)

from pymongo import ASCENDING, DESCENDING
from app.core.database import get_db

def init_db():
    print("🚀 Initializing Database Collections and Indexes...")
    
    db = get_db()
    
    # 1. Users Collections
    # Index: {"auth.email": 1} (Unique)
    # Index: {"auth.uid": 1}
    print("🔹 Setting up 'users' collection...")
    db.users.create_index([("auth.email", ASCENDING)], unique=True)
    db.users.create_index([("auth.uid", ASCENDING)])
    print("   - Created index: auth.email (Unique)")
    print("   - Created index: auth.uid")

    # 2. Keywords Collection (New v1.1 Core)
    # Index: {"keyword_key": 1} (Unique)
    # Index: {"cluster_id": 1}
    print("🔹 Setting up 'keywords' collection...")
    db.keywords.create_index([("keyword_key", ASCENDING)], unique=True)
    # db.keywords.create_index([("cluster_id", ASCENDING)])
    print("   - Created index: keyword_key (Unique)")
    # print("   - Created index: cluster_id")

    # 3. Questions Collection
    # Index: {"primary_keyword": 1}
    print("🔹 Setting up 'questions' collection...")
    db.questions.create_index([("primary_keyword", ASCENDING)])
    print("   - Created index: primary_keyword")

    # 4. Trends Collection
    # Index: {"category": 1} (Unique)
    # Index: {"items.link": 1}
    print("🔹 Setting up 'trends' collection...")
    db.trends.create_index([("category", ASCENDING)], unique=True)
    db.trends.create_index([("items.link", ASCENDING)])
    db.trends.create_index([("items.tags", ASCENDING)])
    print("   - Created index: category (Unique)")
    print("   - Created index: items.link")
    print("   - Created index: items.tags")

    print("\n✅ Database Initialization Completed!")

if __name__ == "__main__":
    try:
        init_db()
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
