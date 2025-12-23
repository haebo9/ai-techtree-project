from pydantic import BaseModel
from .common import MongoDBModel

class Skill(MongoDBModel):
    """
    [Collection]: skills
    개별 기술 메타데이터
    """
    slug: str           # 고유 식별자 (e.g., 'python')
    name: str           # 표시 이름 (e.g., 'Python')
    category: str       # Language, Framework, Database 등
    icon_url: str
    description: str

    class Config:
        json_schema_extra = {
            "example": {
                "slug": "python",
                "name": "Python",
                "category": "Language",
                "description": "Popular programming language"
            }
        }
