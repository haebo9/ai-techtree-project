import os
import sys
import subprocess
import shutil
from pathlib import Path
from dotenv import load_dotenv

# --- 환경변수 로드 ---
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent
env_path = backend_dir / ".env"

load_dotenv(env_path)

MONGODB_URL = os.getenv("MONGODB_URL")

if not MONGODB_URL:
    print("❌ Error: '.env' 파일에 MONGODB_URL 설정이 필요합니다.")
    sys.exit(1)

def migrate_db(source_db: str, target_db: str):
    """
    mongodump -> mongorestore 순차적으로 실행하여 DB 복제(마이그레이션) 작업을 수행합니다.
    """
    backup_dir = current_dir / "mongo_backup"
    
    # 1. 몽고DB 덤프(추출) 커맨드
    dump_cmd = [
        "mongodump",
        f"--uri={MONGODB_URL}",
        f"--db={source_db}",
        f"--out={str(backup_dir)}"
    ]
    
    print(f"\n📦 [1/2] Source DB('{source_db}')에서 데이터 추출 (Dump) 진행 중...")
    try:
        # Popen을 사용하여 쿼리 실행 (에러/출력 확인용)
        # 보안을 위해 로깅 시 비밀번호 부분은 마스킹하여 콘솔에 띄웁니다.
        safe_url = MONGODB_URL.split("@")[1] if "@" in MONGODB_URL else MONGODB_URL
        print(f"   (Using URI: ...@{safe_url})")
        
        subprocess.run(dump_cmd, check=True)
        print("✅ Dump 추출 완료!\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Dump 실패: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ 오류: 'mongodump' 명령어를 찾을 수 없습니다. (MongoDB Database Tools가 단말기에 설치되어 있어야 합니다.)")
        sys.exit(1)
        
    # 2. 몽고DB 복원(붙여넣기) 커맨드
    # mongodump는 지정한 --out 디렉터리 안에 DB 이름으로 폴더를 생성합니다.
    source_dump_path = backup_dir / source_db
    
    restore_cmd = [
        "mongorestore",
        f"--uri={MONGODB_URL}",
        f"--nsFrom={source_db}.*",
        f"--nsTo={target_db}.*",
        str(backup_dir)  # 'ai_techtree_dev' 폴더가 들어있는 부모 폴더를 지정
    ]
    
    print(f"🚀 [2/2] Target DB('{target_db}')로 데이터 복원 (Restore) 진행 중...")
    try:
        subprocess.run(restore_cmd, check=True)
        print("✅ Restore 복원 완료!\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Restore 복원 실패: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ 오류: 'mongorestore' 명령어를 찾을 수 없습니다.")
        sys.exit(1)
        
    print(f"🎉 성공적으로 '{source_db}' 에서 '{target_db}' 로 마이그레이션을 완료했습니다!")
    
    # 3. 임시 백업 폴더 정리 의사 묻기
    print("-" * 50)
    cleanup = input(f"🧹 임시 백업 폴더('{backup_dir}')를 삭제하시겠습니까? (y/n): ")
    if cleanup.lower() == 'y':
        shutil.rmtree(backup_dir, ignore_errors=True)
        print("✅ 임시 백업 폴더가 제거되었습니다.")

if __name__ == "__main__":
    print("=" * 50)
    print(" 🔄 AI TechTree 몽고DB 마이그레이션 툴")
    print("=" * 50)
    print("엔터(Enter) 키만 누르시면 기본값(dev -> prod)으로 진행됩니다.\n")
    
    source = input("🎯 복사할 원본(Source) DB (기본값: 'ai_techtree_dev'): ").strip()
    if not source:
        source = "ai_techtree_dev"
        
    target = input("📥 덮어쓸 대상(Target) DB (기본값: 'ai_techtree_prod'): ").strip()
    if not target:
        target = "ai_techtree_prod"
        
    if source == target:
        print("❌ Source DB와 Target DB의 이름이 같습니다. 마이그레이션을 취소합니다.")
        sys.exit(1)
        
    migrate_db(source, target)
