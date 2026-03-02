import logging
import sys
import os
import httpx

from app.core.config import settings

class TelegramHandler(logging.Handler):
    """
    Custom Logging Handler to send ERROR/CRITICAL logs to Telegram.
    """
    def __init__(self, token: str = None, chat_id: str = None):
        super().__init__()
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage" if self.token else None

    def emit(self, record):
        if not self.token or not self.chat_id:
            return

        try:
            msg = self.format(record)
            # limit telegram msg length
            safe_msg = msg[:4000] 
            env_name = settings.APP_ENV.upper()
            
            payload = {
                "chat_id": self.chat_id,
                "text": f"🚨 *[{env_name}] AI-Techtree Alert*\n\n```text\n{safe_msg}\n```",
                "parse_mode": "Markdown"
            }
            
            with httpx.Client() as client:
                client.post(self.api_url, json=payload, timeout=5.0)
        except Exception:
            self.handleError(record)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # 1. Console (Stdout) Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 2. Telegram Handler (Only send ERROR or CRITICAL)
        telegram_handler = TelegramHandler()
        telegram_handler.setLevel(logging.ERROR)
        telegram_handler.setFormatter(formatter)
        logger.addHandler(telegram_handler)
        
        
    return logger

def send_telegram_message(text: str):
    """
    에러가 아닌 일반 비즈니스 이벤트(알림)를 텔레그램으로 보낼 때 사용하는 범용 함수
    """
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    env_name = settings.APP_ENV.upper()

    if not token or not chat_id:
        return

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": f"📌 *[{env_name}] Notification*\n{text}",
        "parse_mode": "Markdown"
    }
    
    try:
        with httpx.Client() as client:
            client.post(api_url, json=payload, timeout=2.0)
    except Exception as e:
        print(f"텔레그램 일반 전송 실패: {e}")
