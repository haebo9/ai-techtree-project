from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # 필수 환경 변수 (값 없으면 에러 발생)
    OPENAI_API_KEY: str
    MONGODB_URL: str | None = None
    DB_NAME: str = "ai_techtree"  
    
    # 환경 설정
    APP_ENV: str = "LOCAL"  # 기본값 LOCAL
    
    # Telegram Bot 설정 (Settings에서 일괄 관리)
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

    # 선택적 환경 변수 (기본값 제공)
    PROJECT_NAME: str = "AI TechTree"
    API_V1_STR: str = "/api/v1"
    
    @property
    def is_production(self) -> bool:
        return self.APP_ENV.upper() == "PRODUCTION"

    # .env 파일 로드 설정
    model_config = SettingsConfigDict(
        # 리스트의 뒤에 있는 파일(.env.local)이 앞의 파일(.env)을 덮어씁니다.
        env_file=(".env", ".env.local"), 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
