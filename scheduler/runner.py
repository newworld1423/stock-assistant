import schedule
import time
from datetime import datetime
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import RUN_TIME

# 한국 공휴일 (매년 업데이트 필요)
KR_HOLIDAYS_2026 = {
    "20260101", "20260127", "20260128", "20260129", "20260130",
    "20260301", "20260505", "20260506", "20260606", "20260815",
    "20260928", "20260929", "20260930", "20261003", "20261009",
    "20261225",
}

def _is_trading_day() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:  # 토/일
        return False
    today = now.strftime("%Y%m%d")
    if today in KR_HOLIDAYS_2026:
        print(f"[스케줄러] 오늘은 공휴일 — 스킵")
        return False
    return True

def _job():
    if not _is_trading_day():
        return
    print(f"[스케줄러] {datetime.now().strftime('%Y-%m-%d %H:%M')} 작업 시작")
    from main import run
    run()

def start_scheduler():
    print(f"[스케줄러] 데몬 시작 — 평일(공휴일 제외) {RUN_TIME} 실행")
    schedule.every().day.at(RUN_TIME).do(_job)
    while True:
        schedule.run_pending()
        time.sleep(30)
