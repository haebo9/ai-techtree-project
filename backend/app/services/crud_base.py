from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from bson import ObjectId
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorCollection

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    모든 CRUD 서비스의 기본이 되는 부모 클래스입니다.
    제네릭을 사용하여 어떤 모델(User, Interview 등)이든 공통된 메서드로 처리할 수 있습니다.
    """
    def __init__(self, model: Type[ModelType], collection: AsyncIOMotorCollection):
        self.model = model
        self.collection = collection

    async def get(self, id: str) -> Optional[ModelType]:
        """
        [R] 단일 문서 조회
        ID(ObjectId)를 기준으로 문서를 찾아 Pydantic 모델로 변환해 반환합니다.
        """
        if not ObjectId.is_valid(id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        return self.model(**doc) if doc else None

    async def get_multi(
        self, *, skip: int = 0, limit: int = 100, filter_query: Dict[str, Any] = {}
    ) -> List[ModelType]:
        """
        [R] 다중 문서 조회 (페이지네이션)
        조건(filter_query)에 맞는 문서를 skip/limit 하여 리스트로 반환합니다.
        """
        cursor = self.collection.find(filter_query).skip(skip).limit(limit)
        results = []
        async for doc in cursor:
            results.append(self.model(**doc))
        return results

    async def create(self, obj_in: CreateSchemaType | Dict[str, Any]) -> ModelType:
        """
        [C] 문서 생성
        Pydantic 스키마(CreateSchema) 혹은 딕셔너리를 받아 DB에 저장하고, 저장된 객체를 반환합니다.
        """
        if isinstance(obj_in, dict):
            create_data = obj_in
        else:
            create_data = obj_in.model_dump(exclude_unset=True)
            
        result = await self.collection.insert_one(create_data)
        created_doc = await self.collection.find_one({"_id": result.inserted_id})
        return self.model(**created_doc)

    async def update(
        self, id: str, obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> Optional[ModelType]:
        """
        [U] 문서 수정
        ID에 해당하는 문서를 찾아 내용을 업데이트합니다.
        부분 수정(PATCH)을 지원하며, 수정된 최종 객체를 반환합니다.
        """
        if not ObjectId.is_valid(id):
            return None
            
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        if not update_data:
            return await self.get(id)

        await self.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_data}
        )
        return await self.get(id)

    async def delete(self, id: str) -> bool:
        """
        [D] 문서 삭제
        ID에 해당하는 문서를 삭제하고, 성공 여부(bool)를 반환합니다.
        """
        if not ObjectId.is_valid(id):
            return False
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0
