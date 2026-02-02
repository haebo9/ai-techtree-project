
import asyncio
import os
import sys
from datetime import datetime

# Add backend directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(backend_root)

from dotenv import load_dotenv

# Load .env
load_dotenv(os.path.join(backend_root, ".env"))

from app.core.database import db
from app.services.crud_user import user as user_crud
from app.schemas_api.user import UserCreate

async def seed_dummy_user():
    print("🌱 Seeding Dummy Data...")

    dummy_email = "test_user@techtree.com"
    
    # 1. Check if user exists
    existing_user = await user_crud.get_by_email(dummy_email)
    if existing_user:
        print(f"⚠️ User {dummy_email} already exists. Skipping creation.")
        # Optionally delete: await user_crud.delete(str(existing_user.id))
        return

    # 2. Prepared Dummy Data (Direct Dict for DB Model Compatibility)
    # Note: We match the User DB Schema structure, not just API schema.
    user_data = {
        "auth": {
            "email": dummy_email,
            "provider": "local",
            "uid": "dummy_uid_001"
        },
        "profile": {
            "nickname": "Dev_Guru",
            "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Felix",
            "job_title": "Full Stack Developer"
        },
        "stats": {
            "total_stars": 15,
            "completed_tracks": ["Python"]
        },
        "skill_tree": {
            "Python": {
                "level": 2, 
                "stars": 5, 
                "last_tested_at": datetime.utcnow()
            },
            "FastAPI": {
                "level": 1, 
                "stars": 3, 
                "last_tested_at": datetime.utcnow()
            },
            "Docker": {
                "level": 0, 
                "stars": 0,
                "last_tested_at": None
            }
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    try:
        # Create user using CRUD service (which wraps motor insert)
        # Since we constructed the full DB object structure, we can pass it directly 
        # But CRUD create typically expects Schema or Dict.
        new_user = await user_crud.create(user_data)
        print(f"✅ Created Dummy User: {new_user.profile.nickname} (ID: {new_user.id})")
        print(f"   - Tracks: {list(new_user.skill_tree.keys())}")
        print(f"   - Stars: {new_user.stats.total_stars}")

    except Exception as e:
        print(f"❌ Error creating dummy user: {e}")

if __name__ == "__main__":
    if db is None:
        print("❌ Database connection failed. Check MONGODB_URL.")
    else:
        asyncio.run(seed_dummy_user())
