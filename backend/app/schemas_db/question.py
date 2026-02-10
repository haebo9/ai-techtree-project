from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from .common import MongoDBModel

class Question(MongoDBModel):
    """
    [Collection]: questions
    면접 질문 은행 (Static Data)
    각 Subject 및 Level, Keyword에 해당하는 면접 질문과 모범 답안
    """
    subject: Optional[str] = None # Legacy
    level: str              # 'Lv1', 'Lv2', 'Lv3'
    topic: Optional[str] = None # Legacy
    
    # [v1.1] Primary Keyword Link (For direct graph association)
    # Links directly to the `keywords` collection's `keyword_key`
    primary_keyword: Optional[str] = None 
    
    question_text: str
    model_answer: str       # 모범 답안
    
    # 채점 및 검색용 키워드 (Tags associated with the question)
    keywords: List[str] = []
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "subject": "FastAPI Essentials",
                "level": "Lv2",
                "topic": "Dependency Injection",
                "primary_keyword": "Dependency Injection",
                "question_text": "FastAPI에서 DI의 장점은?",
                "model_answer": "DI(Dependency Injection)는 의존성을 외부에서 주입받아 결합도를 낮추는 패턴입니다...",
                "keywords": ["IoC", "Testability", "Coupling"]
            }
        }
