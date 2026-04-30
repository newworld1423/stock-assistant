"""
글로벌 시장 데이터 수집 모듈
- 미국 주요 지수 (나스닥, S&P500, 다우, VIX)
- 달러/원 환율
- 원자재 (WTI, 금)
"""

import yfinance as yf
from datetime import datetime, timedelta
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import US_INDICES


def _get_change(ticker_str: str, period: str = "2d") -> dict:
    """단일 티커 등락률 계산"""
    try:
        t   = yf.Ticker(ticker_str)
        df  = t.history(period=period)
        if len(df) < 2:
            return {"value": None, "change_pct": None, "change_abs": None}

        prev  = df["Close"].iloc[-2]
        close = df["Close"].iloc[-1]
        chg   = ((close / prev) - 1) * 100

        return {
            "value":      round(close, 2),
            "change_pct": round(chg, 2),
            "change_abs": round(close - prev, 2),
        }
    except Exception as e:
        print(f"[글로벌 수집 오류] {ticker_str}: {e}")
        return {"value": None, "change_pct": None, "change_abs": None}


def get_us_indices() -> dict:
    """미국 주요 지수 수집"""
    result = {}
    for name, ticker in US_INDICES.items():
        print(f"  → {name} ({ticker}) 수집 중...")
        result[name] = _get_change(ticker)
    return result


def get_forex() -> dict:
    """환율 수집"""
    return {
        "USD_KRW": _get_change("KRW=X"),
        "USD_JPY": _get_change("JPY=X"),
    }


def get_commodities() -> dict:
    """원자재 수집"""
    return {
        "WTI":  _get_change("CL=F"),
        "금":   _get_change("GC=F"),
    }


def collect_all() -> dict:
    """전체 글로벌 데이터 수집"""
    print("[글로벌] 미국 지수 수집 중...")
    indices = get_us_indices()

    print("[글로벌] 환율 수집 중...")
    forex = get_forex()

    print("[글로벌] 원자재 수집 중...")
    commodities = get_commodities()

    # 시장 분위기 간단 판단 (나스닥 기준)
    nasdaq_chg = indices.get("나스닥", {}).get("change_pct")
    if nasdaq_chg is None:
        sentiment = "알 수 없음"
    elif nasdaq_chg >= 1.0:
        sentiment = "강한 상승"
    elif nasdaq_chg >= 0.3:
        sentiment = "약한 상승"
    elif nasdaq_chg >= -0.3:
        sentiment = "보합"
    elif nasdaq_chg >= -1.0:
        sentiment = "약한 하락"
    else:
        sentiment = "강한 하락"

    data = {
        "us_indices":   indices,
        "forex":        forex,
        "commodities":  commodities,
        "us_sentiment": sentiment,
    }

    print(f"[글로벌] 수집 완료 — 미국 시장: {sentiment} (나스닥 {nasdaq_chg}%)")
    return data


if __name__ == "__main__":
    import json
    result = collect_all()
    print(json.dumps(result, ensure_ascii=False, indent=2))
