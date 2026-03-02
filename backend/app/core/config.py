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
        # 현재 디렉토리 기준과 backend 디렉토리 기준 모두를 탐색 리스트에 넣습니다.
        # 뒤에 오는 파일이 우선순위가 높습니다 (.env.local > .env)
        env_file=(
            ".env", 
            "backend/.env", 
            ".env.local", 
            "backend/.env.local"
        ), 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
