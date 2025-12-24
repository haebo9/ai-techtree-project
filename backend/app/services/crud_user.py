from app.schemas_db.user import User
from app.schemas_api.user import UserCreate, UserUpdate
from app.services.crud_base import CRUDBase
from app.core.database import db

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """
    User 모델 전용 CRUD 로직.
    기본 CRUD 외에 이메일 조회 등 사용자 특화 기능을 추가합니다.
    """
    async def get_by_email(self, email: str) -> User | None:
        """이메일로 사용자 조회 (로그인 시 사용)"""
        doc = await self.collection.find_one({"auth.email": email})
        return self.model(**doc) if doc else None

user = CRUDUser(User, db.users)
