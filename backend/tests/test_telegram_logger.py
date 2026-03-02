import sys
import os
import time

# --- Setup PYTHONPATH for simple testing ---
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

from app.core.logger import get_logger

# 1. 테스트용 로거 생성
logger = get_logger("telegram_test_logger")

def trigger_test_error():
    """
    고의로 Exception을 발생시키고 logger.error()를 호출하여
    텔레그램 알림 핸들러가 정상적으로 동작하는지 확인하는 함수.
    """
    print("🚀 [1/3] 텔레그램 알림 시스템 활성화를 위한 테스트 에러를 유발합니다...")
    time.sleep(1)
    
    try:
        print("💥 [2/3] 의도적인 'ZeroDivisionError' 발생 중...")
        # 의도된 수학적 오류 발생 (0으로 나누기)
        result = 100 / 0
        
    except Exception as e:
        # 이 시점에 에러 로그가 찍히며 자동으로 텔레그램 봇으로 전송되어야 합니다.
        print("📲 [3/3] 에러 캐치! logger.error()를 트리거합니다. (텔레그램을 확인하세요!)")
        
        # 실제 환경과 동일하게 exc_info=True 를 주어 스택 트레이스도 전송.
        logger.error(f"🐛 [TEST ERROR] 의도된 테스트 에러입니다: {e}", exc_info=True)

if __name__ == "__main__":
    if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
        print("🚫 [경고] .env 파일에 TELEGRAM_BOT_TOKEN 혹은 TELEGRAM_CHAT_ID가 없습니다.")
        print("설정한 뒤 다시 실행해 주세요!")
    else:
        trigger_test_error()
        print("✅ 테스트 스크립트 실행이 완료되었습니다!")
