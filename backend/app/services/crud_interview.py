from app.schemas_db.interview import Interview
from app.schemas_api.interview import InterviewCreate, InterviewUpdate
from app.services.crud_base import CRUDBase
from app.core.database import db

class CRUDInterview(CRUDBase[Interview, InterviewCreate, InterviewUpdate]):
    """
    Interview 모델 전용 CRUD 로직.
    현재는 기본 CRUDBase 기능만 사용하지만, 추후 '특정 스킬의 면접 내역 조회' 등의 기능이 추가될 수 있습니다.
    """
    pass

interview = CRUDInterview(Interview, db.interviews)
