from app.services.crud_base import CRUDBase
from app.schemas_db.chat_log import ChatLog
from app.core.database import db

class CRUDChatLog(CRUDBase[ChatLog, ChatLog, ChatLog]):
    async def create_log(self, data: dict) -> ChatLog:
        return await self.create(obj_in=data)

chat_log = CRUDChatLog(ChatLog, db.chat_logs)
