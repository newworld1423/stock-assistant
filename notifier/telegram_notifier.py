"""
텔레그램 봇 알림 모듈
- Claude 분석 결과를 보기 좋은 메시지로 변환
- 텔레그램 채팅으로 전송
"""

import requests
import json
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

RISK_EMOJI = {"상": "🔴", "중": "🟡", "하": "🟢"}
STYLE_EMOJI = {
    "갭 상승 추종": "📈",
    "모멘텀":       "🚀",
    "눌림목 반등":  "↩️",
    "돌파 매매":    "💥",
}
SENTIMENT_EMOJI = {
    "강한 상승": "🚀",
    "약한 상승": "📈",
    "보합":     "➡️",
    "약한 하락": "📉",
    "강한 하락": "💣",
}
OUTLOOK_EMOJI = {"긍정": "✅", "중립": "⚪", "부정": "❌"}


def _build_message(result: dict) -> str:
    """분석 결과 → 텔레그램 메시지 변환"""

    if "error" in result:
        return f"⚠️ 분석 오류\n{result.get('error', '')}"

    lines = []
    date  = result.get("report_date", "")
    ov    = result.get("market_overview", {})

    # ── 헤더 ──────────────────────────────────────────────────────────────────
    us_sent = ov.get("us_sentiment", "")
    kospi   = ov.get("kospi_outlook", "")
    lines.append(f"📊 *오늘의 데이트레이딩 브리핑* — {date}")
    lines.append("━" * 28)
    lines.append(
        f"{SENTIMENT_EMOJI.get(us_sent, '➡️')} 미국 시장: *{us_sent}*   "
        f"{OUTLOOK_EMOJI.get(kospi, '⚪')} 코스피: *{kospi}*"
    )
    lines.append(f"💡 핵심 변수: {ov.get('key_factor', '')}")

    caution = ov.get("caution")
    if caution:
        lines.append(f"⚠️ 주의: {caution}")

    # ── 테마 ──────────────────────────────────────────────────────────────────
    theme = result.get("theme_of_day")
    if theme:
        lines.append(f"🎯 오늘의 테마: *{theme}*")

    # ── 종목 픽 ───────────────────────────────────────────────────────────────
    picks = result.get("picks", [])
    lines.append(f"\n🔍 *오늘의 후보 종목 ({len(picks)}개)*")
    lines.append("━" * 28)

    for p in picks:
        risk  = p.get("risk_level", "중")
        style = p.get("trade_style", "")
        lines.append(
            f"\n*{p['rank']}위* {RISK_EMOJI.get(risk, '🟡')} "
            f"{p['name']} ({p['ticker']}) [{p['market']}]"
        )
        lines.append(f"  {STYLE_EMOJI.get(style, '📌')} {style}")
        lines.append(f"  전일 종가: {p.get('close', 0):,}원")
        lines.append(f"  📝 {p.get('reason', '')}")
        lines.append(f"  🎯 진입: {p.get('entry_strategy', '')}")
        lines.append(f"  🛑 손절: `{p.get('stop_loss', '')}`")
        lines.append(f"  ✅ 목표1: {p.get('target_1', '')}  목표2: {p.get('target_2', '')}")

    # ── 회피 종목 ─────────────────────────────────────────────────────────────
    avoid = result.get("avoid_today", [])
    if avoid:
        lines.append("\n⛔ *오늘 피할 것들*")
        for item in avoid:
            lines.append(f"  • {item}")

    lines.append("\n━" * 28)
    lines.append("_⚠️ 본 분석은 참고용입니다. 투자 결정은 본인 판단으로._")

    return "\n".join(lines)


def send(result: dict) -> bool:
    """텔레그램으로 분석 결과 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[텔레그램] BOT_TOKEN 또는 CHAT_ID 미설정 — 콘솔 출력으로 대체")
        print("=" * 50)
        print(_build_message(result))
        print("=" * 50)
        return True

    message = _build_message(result)
    url     = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # 텔레그램 메시지 길이 제한 4096자 → 초과 시 분할 전송
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]

    success = True
    for idx, chunk in enumerate(chunks):
        try:
            resp = requests.post(
                url,
                json={
                    "chat_id":    TELEGRAM_CHAT_ID,
                    "text":       chunk,
                    "parse_mode": "Markdown",
                },
                timeout=15,
            )
            data = resp.json()
            if not data.get("ok"):
                print(f"[텔레그램] 전송 실패 (청크 {idx+1}): {data}")
                success = False
        except Exception as e:
            print(f"[텔레그램] 오류 (청크 {idx+1}): {e}")
            success = False

    if success:
        print(f"[텔레그램] 전송 완료 ({len(chunks)}개 청크)")
    return success


def send_error(message: str) -> None:
    """오류 발생 시 텔레그램으로 알림"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[ERROR] {message}")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text":    f"🚨 주식 비서 오류\n{message}",
            },
            timeout=10,
        )
    except Exception:
        pass


if __name__ == "__main__":
    # 테스트용 더미 결과
    dummy = {
        "report_date": "2024-12-16",
        "market_overview": {
            "us_sentiment": "약한 상승",
            "kospi_outlook": "긍정",
            "key_factor": "나스닥 +1.2% 상승 마감, 반도체 섹터 수혜 기대",
            "caution": "오후 FOMC 의사록 발표 예정 — 오후 변동성 주의",
        },
        "picks": [
            {
                "rank": 1, "ticker": "005930", "name": "삼성전자",
                "market": "KOSPI", "close": 75000,
                "reason": "외국인 1,200억 순매수, HBM 수주 기대감 지속. 나스닥 강세 직접 수혜.",
                "entry_strategy": "9:05 이후 75,000원 지지 확인 후 분할 매수",
                "stop_loss": "73,500원 (-2.0%) 이탈 시 즉시 손절",
                "target_1": "76,500원 (+2.0%)", "target_2": "78,000원 (+4.0%)",
                "risk_level": "하", "trade_style": "모멘텀",
            }
        ],
        "avoid_today": ["코스닥 소형주 — 뚜렷한 테마 없이 변동성만 높음"],
        "theme_of_day": "AI 반도체 (삼성전자, SK하이닉스, 한미반도체)",
    }
    send(dummy)
