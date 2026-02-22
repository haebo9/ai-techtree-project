import asyncio
import os
import sys

# Add the project root (backend) to sys.path so 'app' can be resolved
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import client, db
from app.schemas_db.user import User, AuthInfo, UserProfile, KeywordProgress
from app.services.crud_user import user as user_crud

async def create_dummy_data():
    if db is None:
        print("Database not connected. Check MONGODB_URL mapping in .env")
        return

    print("--- Creating Dummy Test User ---")
    
    # 랭그래프 퀴즈 테스트를 위한 사용자 이메일
    test_email = "test_user@ai-techtree.com" 
    
    # 기존 사용자 확인
    existing_user = await user_crud.get_by_email(test_email)
    
    if existing_user:
        print(f"Test user already exists with ID: {existing_user.id}")
        user_id = existing_user.id
    else:
        # 더미 사용자 데이터 생성
        new_user = User(
            auth=AuthInfo(email=test_email, provider="test", uid="test_uid_001"),
            profile=UserProfile(nickname="TestUser"),
            keyword_progress={
                "Dependency Injection": KeywordProgress(star=1),
                "FastAPI": KeywordProgress(star=0)
            },
            recommended_keywords=["FastAPI", "AsyncIO"]
        )
        
        # Insert directly to DB to bypass API schema validation in dummy script
        user_dict = new_user.model_dump(by_alias=True, exclude={"id"})
        result = await db.users.insert_one(user_dict)
        user_id = str(result.inserted_id)
        print(f"Test user created with ID: {user_id}")


    print("\n[SUCCESS] Dummy data population complete!")
    print(f"Test User ID: {user_id}")
    print("Please use this user_id/user_db_id in your test scripts.")

    if client:
        client.close()

if __name__ == "__main__":
    asyncio.run(create_dummy_data())
