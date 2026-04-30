"""
주식 비서 메인 실행 파일
실행: python main.py
"""

import json
import os
import sys
from datetime import datetime
import traceback

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(__file__))

from collectors.krx_collector    import collect_all as collect_krx
from collectors.global_collector  import collect_all as collect_global
from collectors.news_collector    import collect_all as collect_news
from analyzer.claude_analyzer     import analyze
from notifier.kakao_notifier      import send, send_error
from config                       import LOG_DIR


def save_log(data: dict, label: str) -> None:
    """수집/분석 결과를 로그 파일로 저장"""
    os.makedirs(LOG_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    path = os.path.join(LOG_DIR, f"{date_str}_{label}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[로그] 저장: {path}")


def run():
    print("=" * 50)
    print(f"🚀 주식 비서 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    try:
        # ── Step 1: 데이터 수집 ─────────────────────────────────────────────
        print("\n[1/3] 데이터 수집 중...")
        krx_data    = collect_krx()
        global_data = collect_global()
        news_data   = collect_news()

        # 수집 데이터 로그 저장
        save_log({
            "krx":    krx_data,
            "global": global_data,
            "news":   news_data,
        }, "collected")

        # ── Step 2: Claude 분석 ─────────────────────────────────────────────
        print("\n[2/3] Claude 분석 중...")
        result = analyze(krx_data, global_data, news_data)

        # 분석 결과 로그 저장
        save_log(result, "analysis")

        # ── Step 3: 텔레그램 전송 ───────────────────────────────────────────
        print("\n[3/3] 텔레그램 전송 중...")
        send(result)

        print("\n✅ 완료!")
        return True

    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        print(f"\n❌ 오류 발생:\n{err_msg}")
        send_error(err_msg[:500])
        return False


if __name__ == "__main__":
    # 커맨드라인 인수 처리
    # python main.py           → 즉시 1회 실행
    # python main.py --daemon  → 스케줄러 모드 (매일 자동)
    if "--daemon" in sys.argv:
        from scheduler.runner import start_scheduler
        start_scheduler()
    else:
        run()
