import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID", "")

# ── 수집 설정 ──────────────────────────────────────────────────────────────────
MARKETS             = ["KOSPI", "KOSDAQ"]   # 분석 시장
TOP_VOLUME_COUNT    = 30                    # 거래량 상위 몇 개
FOREIGN_TOP_COUNT   = 15                    # 외국인 순매수 상위 몇 개
MAX_PICKS           = int(os.getenv("MAX_PICKS", 5))  # Claude 최종 추천 수

# ── 스케줄 설정 ────────────────────────────────────────────────────────────────
# 평일 오전 8시 10분 (장 시작 50분 전) 실행
RUN_TIME            = "08:10"

# ── 미국 지수 티커 ──────────────────────────────────────────────────────────────
US_INDICES = {
    "나스닥":   "^IXIC",
    "S&P500":  "^GSPC",
    "다우":     "^DJI",
    "VIX":     "^VIX",
}

# ── Claude 모델 ────────────────────────────────────────────────────────────────
CLAUDE_MODEL        = "claude-opus-4-5"

# ── 로그 경로 ──────────────────────────────────────────────────────────────────
LOG_DIR             = os.path.join(os.path.dirname(__file__), "logs")
