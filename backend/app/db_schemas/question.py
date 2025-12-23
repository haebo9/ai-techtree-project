from typing import List, Optional
from pydantic import BaseModel
from .common import MongoDBModel

class Question(MongoDBModel):
    """
    [Collection]: questions
    면접 질문 은행 (Static Data)
    """
    skill_slug: str         # e.g., 'python'
    level: int              # 난이도 (1, 2, 3)
    topic: str              # e.g., 'Generator', 'GIL'
    
    question_text: str
    model_answer: str       # 모범 답안
    
    # 평가 기준 키워드 (채점 시 활용)
    evaluation_criteria: List[str] = []

    class Config:
        json_schema_extra = {
            "example": {
                "skill_slug": "python",
                "level": 2,
                "topic": "Generator",
                "question_text": "Generator와 일반 함수의 차이는?",
                "evaluation_criteria": ["yield", "memory efficiency"]
            }
        }
