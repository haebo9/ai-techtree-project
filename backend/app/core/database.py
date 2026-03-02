from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# 1. Initialize MongoDB Client
# Motor client is lazy, so it is safe to create global instance on import.
if settings.MONGODB_URL:
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    # 2. Export Database Instance
    # This allows 'db.collection_name' access in CRUD modules
    db = client[settings.DB_NAME]
else:
    # Fallback or startup warning
    print("⚠️ MONGODB_URL is not set. Database features will fail.")
    client = None
    db = None

def get_db():
    """
    Returns the database instance.
    """
    return db
