import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.schemas_db.user import User

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["ai_techtree"]
    
    doc = await db.users.find_one({"auth.email": "haebo9@guest.com"})
    print("Doc found:", doc)
    if doc:
        try:
            user = User(**doc)
            print("Parsed user:", user)
        except Exception as e:
            print("Parse error:", e)

if __name__ == "__main__":
    asyncio.run(main())
