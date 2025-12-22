from typing import Annotated, Any
from pydantic import BaseModel, BeforeValidator, Field

# ObjectId를 문자열로 자동 변환 처리
PyObjectId = Annotated[str, BeforeValidator(str)]

class MongoDBModel(BaseModel):
    """
    모든 MongoDB 모델의 부모 클래스.
    _id 필드를 id로 매핑하여 파이썬 객체로 다룰 때 편리하게 함.
    """
    id: PyObjectId | None = Field(default=None, alias="_id")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
