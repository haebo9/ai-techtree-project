from app.services.crud_base import CRUDBase
from app.schemas_db.keyword import Keyword
from app.core.database import db

# We use the Keyword model for Create/Update schemas for simplicity in this MVP
class CRUDKeyword(CRUDBase[Keyword, Keyword, Keyword]):
    
    async def get_by_key(self, keyword_key: str) -> Keyword | None:
        """
        Retrieves a keyword document by its unique 'keyword_key'.
        """
        doc = await self.collection.find_one({"keyword_key": keyword_key})
        if doc:
            return self.model(**doc)
        return None

# Instantiate with 'keywords' collection
keyword = CRUDKeyword(Keyword, db.keywords)
