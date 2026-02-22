import asyncio
from app.services.embedding_service import embedding_service
from app.services.crud_user import user as user_crud
from app.services.crud_keyword import keyword as keyword_crud

async def test():
    user = await user_crud.get_by_email("test_user@ai-techtree.com")
    if not user:
        print("User not found")
        return
    print(f"Before: {user.recommended_keywords}")
    print(f"User ID: {user.id}")
    
    await embedding_service.calculate_recommendation("test_user@ai-techtree.com")
    
    user2 = await user_crud.get_by_email("test_user@ai-techtree.com")
    print(f"After : {user2.recommended_keywords}")

if __name__ == "__main__":
    asyncio.run(test())
