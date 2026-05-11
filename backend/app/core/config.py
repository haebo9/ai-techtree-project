from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # 필수 환경 변수 (값 없으면 에러 발생)
    OPENAI_API_KEY: str
    TAVILY_API_KEY: str | None = None
    MONGODB_URL: str | None = None
    DB_NAME: str = "ai_techtree"  
    
    # 환경 설정
    APP_ENV: str = "LOCAL"  # 기본값 LOCAL
    
    # Telegram Bot 설정 (Settings에서 일괄 관리)
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

    # 이메일 전송 (Resend API) 설정
    RESEND_API_KEY: str | None = None

    # Reflexion 로컬 학습 저장소
    REFLECTION_STORE_PATH: str = "backend/app/source/interview_reflections.jsonl"
    POLICY_STORE_PATH: str = "backend/app/source/interview_policies.jsonl"
    REFLECTION_STORAGE_BACKEND: str = "auto"  # auto | mongo | jsonl
    REFLECTION_DB_NAME: str = "reflection"
    REFLECTION_VECTOR_SEARCH_ENABLED: bool = True
    REFLECTION_VECTOR_INDEX_NAME: str = "reflection_vector_index"
    REFLECTION_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # 선택적 환경 변수 (기본값 제공)
    PROJECT_NAME: str = "TechTree"
    VERSION: str = "2.0.0"
    
    @property
    def is_production(self) -> bool:
        return self.APP_ENV.upper() == "PRODUCTION"

    # .env 파일 로드 설정 (Docker 환경변수가 파일보다 우선순위가 높습니다)
    model_config = SettingsConfigDict(
        # 리스트의 뒤로 갈수록 우선순위가 높습니다. 
        # 로직: .env (기본) -> .env.local (로컬 개발용 덮어쓰기)
        env_file=[
            "backend/.env",
            ".env",
            "backend/.env.local",
            ".env.local",
        ],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
