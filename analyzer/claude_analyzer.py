"""
Claude API를 사용한 종목 분석 모듈
- 수집된 데이터를 정형화하여 Claude에 전달
- JSON 형태의 분석 결과 반환
"""

import anthropic
import json
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_PICKS


# ── 시스템 프롬프트 ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
당신은 한국 주식 데이트레이딩 전문 퀀트 애널리스트입니다.
매일 장 시작 전, 수집된 시장 데이터를 분석하여 당일 데이트레이딩 후보 종목을 선별합니다.

## 분석 철학
- 데이트레이딩 특성상 **당일 모멘텀과 거래량**을 최우선으로 평가합니다
- 전날 외국인/기관 동반 순매수는 강한 수급 신호로 봅니다
- 미국 시장 강세 → 코스피 대형주 수혜 / 약세 → 내수 방어주 선별
- VIX 20 이상이면 변동성 경고를 반드시 언급합니다
- **확신이 없는 종목은 절대 추천하지 않습니다** (3개만 나와도 됩니다)
- 손절 기준 없이는 어떤 종목도 추천하지 않습니다

## 데이트레이딩 진입 전략
- 장 초반(9:00~9:30): 갭 방향 확인 후 추세 추종
- 중반(9:30~11:00): 거래량 터지는 종목 모멘텀 매매
- 손절: 진입가 대비 -1.5% ~ -2.5%를 기본으로 제시
- 목표: 리스크 대비 2~3배 수익 구간 제시

## 출력 형식
반드시 아래 JSON만 출력하세요. 마크다운, 코드블럭, 설명 텍스트 절대 금지.

{
  "report_date": "YYYY-MM-DD",
  "market_overview": {
    "us_sentiment": "강한 상승|약한 상승|보합|약한 하락|강한 하락",
    "kospi_outlook": "긍정|중립|부정",
    "key_factor": "오늘 장을 움직일 핵심 변수 한 줄",
    "caution": "오늘 특히 주의할 점 (없으면 null)"
  },
  "picks": [
    {
      "rank": 1,
      "ticker": "005930",
      "name": "삼성전자",
      "market": "KOSPI",
      "close": 75000,
      "reason": "선정 근거 (2~3줄, 구체적인 수치 포함)",
      "entry_strategy": "장 시작 후 9시 5분 이후 75,000원 지지 확인 후 매수",
      "stop_loss": "73,500원 (-2.0%) 이탈 시 즉시 손절",
      "target_1": "76,500원 (+2.0%)",
      "target_2": "78,000원 (+4.0%)",
      "risk_level": "상|중|하",
      "trade_style": "갭 상승 추종|모멘텀|눌림목 반등|돌파 매매"
    }
  ],
  "avoid_today": ["오늘 피해야 할 종목 또는 섹터 (이유 포함)"],
  "theme_of_day": "오늘 주목할 테마 섹터"
}
"""


def _format_krx_data(krx: dict) -> str:
    """KRX 데이터를 Claude가 읽기 쉬운 텍스트로 변환"""
    lines = []

    lines.append("=== 전일 거래량 상위 종목 ===")
    for i, s in enumerate(krx.get("top_volume", [])[:20], 1):
        lines.append(
            f"{i}. [{s['market']}] {s['name']}({s['ticker']}) "
            f"종가:{s['close']:,}원 거래량:{s['volume']:,} 등락:{s['change_pct']:+.1f}%"
        )

    lines.append("\n=== 외국인 순매수 상위 ===")
    for i, s in enumerate(krx.get("foreign_buy", [])[:15], 1):
        lines.append(
            f"{i}. [{s['market']}] {s['name']}({s['ticker']}) "
            f"외국인순매수:{s['foreign_net']:,}원 기관:{s['inst_net']:,}원 "
            f"종가:{s['close']:,}원 등락:{s['change_pct']:+.1f}%"
        )

    lines.append("\n=== 전일 급등 상위 ===")
    for i, s in enumerate(krx.get("top_gainers", [])[:10], 1):
        lines.append(
            f"{i}. [{s['market']}] {s['name']}({s['ticker']}) "
            f"등락:{s['change_pct']:+.1f}% 종가:{s['close']:,}원 거래량:{s['volume']:,}"
        )

    return "\n".join(lines)


def _format_global_data(glb: dict) -> str:
    """글로벌 데이터 포맷"""
    lines = ["=== 미국 시장 (전일 마감) ==="]
    for name, info in glb.get("us_indices", {}).items():
        v   = info.get("value", "N/A")
        chg = info.get("change_pct")
        chg_str = f"{chg:+.2f}%" if chg is not None else "N/A"
        lines.append(f"  {name}: {v} ({chg_str})")

    lines.append("\n=== 환율 ===")
    usd_krw = glb.get("forex", {}).get("USD_KRW", {})
    lines.append(f"  달러/원: {usd_krw.get('value', 'N/A')}원 ({usd_krw.get('change_pct', 'N/A')}%)")

    lines.append("\n=== 원자재 ===")
    wti = glb.get("commodities", {}).get("WTI", {})
    gold = glb.get("commodities", {}).get("금", {})
    lines.append(f"  WTI: ${wti.get('value', 'N/A')} ({wti.get('change_pct', 'N/A')}%)")
    lines.append(f"  금: ${gold.get('value', 'N/A')} ({gold.get('change_pct', 'N/A')}%)")

    lines.append(f"\n미국 시장 분위기: {glb.get('us_sentiment', '알 수 없음')}")
    return "\n".join(lines)


def _format_news_data(news: dict) -> str:
    """뉴스 데이터 포맷"""
    lines = ["=== 오늘 주요 뉴스 ==="]
    for item in news.get("news", [])[:8]:
        lines.append(f"  - {item['title']}")

    disclosures = news.get("disclosures", [])
    if disclosures:
        lines.append("\n=== 오늘 주요 공시 ===")
        for item in disclosures[:5]:
            lines.append(f"  [{item['company']}] {item['title']}")

    return "\n".join(lines)


def analyze(krx_data: dict, global_data: dict, news_data: dict) -> dict:
    """
    Claude API에 분석 요청 후 결과 반환
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    report_date = datetime.now().strftime("%Y-%m-%d")
    today_weekday = ["월", "화", "수", "목", "금", "토", "일"][datetime.now().weekday()]

    user_prompt = f"""
분석 날짜: {report_date} ({today_weekday}요일)
데이터 기준: {krx_data.get('date', '전일')}

{_format_global_data(global_data)}

{_format_krx_data(krx_data)}

{_format_news_data(news_data)}

위 데이터를 종합 분석하여 오늘 데이트레이딩 후보 종목 최대 {MAX_PICKS}개를 선정해주세요.
각 종목의 진입 전략, 손절 기준, 목표가를 반드시 포함하세요.
"""

    print("[Claude] API 호출 중...")
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        raw = response.content[0].text.strip()

        # JSON 파싱
        # 혹시 ```json 블록이 포함되어 있으면 제거
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)
        print(f"[Claude] 분석 완료 — picks: {len(result.get('picks', []))}개")
        return result

    except json.JSONDecodeError as e:
        print(f"[Claude] JSON 파싱 오류: {e}")
        print(f"원본 응답:\n{raw}")
        return {"error": "JSON 파싱 실패", "raw": raw}
    except Exception as e:
        print(f"[Claude] API 오류: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # 테스트용 더미 데이터
    dummy_krx = {
        "date": "20241215",
        "top_volume": [
            {"ticker": "005930", "name": "삼성전자", "market": "KOSPI",
             "close": 75000, "volume": 15000000, "change_pct": 1.5},
        ],
        "foreign_buy": [],
        "top_gainers": [],
    }
    dummy_global = {
        "us_indices": {"나스닥": {"value": 19000, "change_pct": 1.2}},
        "forex": {"USD_KRW": {"value": 1320, "change_pct": -0.3}},
        "commodities": {"WTI": {"value": 70, "change_pct": 0.5}, "금": {"value": 2050, "change_pct": 0.2}},
        "us_sentiment": "약한 상승",
    }
    dummy_news = {"news": [{"title": "삼성전자 HBM 수주 기대감"}], "disclosures": []}

    result = analyze(dummy_krx, dummy_global, dummy_news)
    print(json.dumps(result, ensure_ascii=False, indent=2))
