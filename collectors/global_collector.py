"""
글로벌 시장 데이터 수집 - 네이버 금융 기반
yfinance 대신 네이버 금융 사용 (GitHub Actions 환경에서 안정적)
"""

import requests
from datetime import datetime
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com/",
}

# 네이버 금융 해외 지수 코드
NAVER_INDICES = {
    "나스닥":  "NAS",
    "S&P500": "SPI",
    "다우":    "DJI",
    "VIX":    "VIX",
}


def _get_naver_world_index(code: str) -> dict:
    """네이버 금융 해외 지수 조회"""
    try:
        url = f"https://finance.naver.com/world/sise.naver?symbol={code}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "utf-8"
        text = resp.text

        # 현재가 파싱
        value = None
        change_pct = None

        if 'now' in text:
            try:
                now_part = text.split('"now"')[1].split(',')[0]
                value = float(''.join(c for c in now_part if c.isdigit() or c == '.'))
            except Exception:
                pass

        if 'rate' in text:
            try:
                rate_part = text.split('"rate"')[1].split(',')[0]
                change_pct = float(''.join(c for c in rate_part if c.isdigit() or c in '.-'))
                if '-' in rate_part:
                    change_pct = -abs(change_pct)
            except Exception:
                pass

        return {"value": value, "change_pct": change_pct, "change_abs": None}
    except Exception as e:
        return {"value": None, "change_pct": None, "change_abs": None}


def _get_naver_exchange_rate() -> dict:
    """네이버 금융 환율 조회"""
    try:
        url = "https://finance.naver.com/marketindex/"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "euc-kr"
        text = resp.text

        usd_krw = None
        if "USD" in text and "exchangeList" in text:
            try:
                usd_part = text.split('data-exchange-list')[1] if 'data-exchange-list' in text else text
                # 간단 파싱
                parts = text.split('USD/KRW')
                if len(parts) > 1:
                    nums = ''.join(c for c in parts[1][:50] if c.isdigit() or c == '.')
                    if nums:
                        usd_krw = float(nums[:7])
            except Exception:
                pass

        return {
            "USD_KRW": {"value": usd_krw, "change_pct": None, "change_abs": None}
        }
    except Exception as e:
        return {"USD_KRW": {"value": None, "change_pct": None, "change_abs": None}}


def get_us_indices() -> dict:
    result = {}
    for name, code in NAVER_INDICES.items():
        print(f"  → {name} ({code}) 수집 중...")
        result[name] = _get_naver_world_index(code)
    return result


def get_forex() -> dict:
    return _get_naver_exchange_rate()


def get_commodities() -> dict:
    return {
        "WTI":  _get_naver_world_index("OIL"),
        "금":   _get_naver_world_index("GLD"),
    }


def collect_all() -> dict:
    print("[글로벌] 미국 지수 수집 중...")
    indices = get_us_indices()

    print("[글로벌] 환율 수집 중...")
    forex = get_forex()

    print("[글로벌] 원자재 수집 중...")
    commodities = get_commodities()

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
