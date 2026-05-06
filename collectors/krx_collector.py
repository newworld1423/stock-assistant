"""
KRX 데이터 수집 - 네이버 금융 크롤링 방식
pykrx 대신 네이버 금융 API 사용 (GitHub Actions 환경에서도 안정적)
"""

import requests
import json
from datetime import datetime, timedelta
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import MARKETS, TOP_VOLUME_COUNT, FOREIGN_TOP_COUNT

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com/",
}


def _last_trading_day() -> str:
    today = datetime.now()
    offset = {0: 3, 6: 2}.get(today.weekday(), 1)
    return (today - timedelta(days=offset)).strftime("%Y%m%d")


def get_top_volume(market: str) -> list:
    """네이버 금융 거래량 상위 종목"""
    try:
        market_code = "KOSPI" if market == "KOSPI" else "KOSDAQ"
        url = (
            f"https://finance.naver.com/sise/sise_quant.naver"
            f"?sosok={'0' if market == 'KOSPI' else '1'}"
        )
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "euc-kr"
        text = resp.text

        results = []
        # 종목 파싱 (네이버 금융 테이블)
        rows = text.split('<tr onmouseover')[1:]
        for row in rows[:TOP_VOLUME_COUNT]:
            try:
                # 종목코드
                code = row.split("code=")[1].split('"')[0].strip()
                # 종목명
                name = row.split('title="')[1].split('"')[0].strip() if 'title="' in row else ""
                if not name:
                    name = row.split("</a>")[0].split(">")[-1].strip()
                # 현재가
                tds = row.split("<td")
                close = 0
                volume = 0
                change_pct = 0.0
                td_texts = []
                for td in tds[1:]:
                    val = td.split("</td>")[0]
                    val = ''.join(c for c in val if c.isdigit() or c in '.-+')
                    td_texts.append(val)

                if len(td_texts) >= 3:
                    try:
                        close = int(td_texts[0].replace(',', '')) if td_texts[0] else 0
                    except Exception:
                        pass
                    try:
                        volume_str = [t for t in td_texts if len(t) > 4]
                        volume = int(volume_str[0].replace(',', '')) if volume_str else 0
                    except Exception:
                        pass

                if code and name and len(code) == 6:
                    results.append({
                        "ticker":     code,
                        "name":       name,
                        "market":     market,
                        "close":      close,
                        "volume":     volume,
                        "change_pct": change_pct,
                    })
            except Exception:
                continue

        print(f"  [네이버] {market} 거래량 상위 {len(results)}개 수집")
        return results
    except Exception as e:
        print(f"[거래량 수집 오류] {market}: {e}")
        return []


def get_top_gainers(market: str, top_n: int = 10) -> list:
    """네이버 금융 상승률 상위"""
    try:
        url = (
            f"https://finance.naver.com/sise/sise_rise.naver"
            f"?sosok={'0' if market == 'KOSPI' else '1'}"
        )
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "euc-kr"
        text = resp.text

        results = []
        rows = text.split('<tr onmouseover')[1:]
        for row in rows[:top_n]:
            try:
                code = row.split("code=")[1].split('"')[0].strip()
                name = row.split('title="')[1].split('"')[0].strip() if 'title="' in row else ""
                if not name:
                    name = row.split("</a>")[0].split(">")[-1].strip()

                if code and name and len(code) == 6:
                    results.append({
                        "ticker":     code,
                        "name":       name,
                        "market":     market,
                        "close":      0,
                        "change_pct": 0.0,
                        "volume":     0,
                    })
            except Exception:
                continue

        print(f"  [네이버] {market} 급등주 {len(results)}개 수집")
        return results
    except Exception as e:
        print(f"[급등 수집 오류] {market}: {e}")
        return []


def get_foreign_net_buy(market: str) -> list:
    """네이버 금융 외국인 순매수 상위"""
    try:
        url = (
            f"https://finance.naver.com/sise/sise_foreign.naver"
            f"?sosok={'0' if market == 'KOSPI' else '1'}"
        )
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "euc-kr"
        text = resp.text

        results = []
        rows = text.split('<tr onmouseover')[1:]
        for row in rows[:FOREIGN_TOP_COUNT]:
            try:
                code = row.split("code=")[1].split('"')[0].strip()
                name = row.split('title="')[1].split('"')[0].strip() if 'title="' in row else ""
                if not name:
                    name = row.split("</a>")[0].split(">")[-1].strip()

                if code and name and len(code) == 6:
                    results.append({
                        "ticker":      code,
                        "name":        name,
                        "market":      market,
                        "foreign_net": 0,
                        "inst_net":    0,
                        "close":       0,
                        "change_pct":  0.0,
                    })
            except Exception:
                continue

        print(f"  [네이버] {market} 외국인 순매수 {len(results)}개 수집")
        return results
    except Exception as e:
        print(f"[외국인 수집 오류] {market}: {e}")
        return []


def get_market_summary() -> dict:
    """코스피/코스닥 지수 현황"""
    try:
        url = "https://finance.naver.com/sise/sise_index.naver?code=KOSPI"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "euc-kr"
        return {"status": "ok"}
    except Exception:
        return {}


def collect_all(date: str = None) -> dict:
    if date is None:
        date = _last_trading_day()

    print(f"[KRX] 수집 날짜: {date}")
    data = {"date": date, "top_volume": [], "foreign_buy": [], "top_gainers": []}

    for market in MARKETS:
        print(f"  → {market} 거래량 상위 수집 중...")
        data["top_volume"]  += get_top_volume(market)
        print(f"  → {market} 외국인 순매수 수집 중...")
        data["foreign_buy"] += get_foreign_net_buy(market)
        print(f"  → {market} 급등주 수집 중...")
        data["top_gainers"] += get_top_gainers(market)

    data["top_volume"].sort(key=lambda x: x["volume"], reverse=True)

    print(f"[KRX] 수집 완료 — 거래량:{len(data['top_volume'])} 외국인:{len(data['foreign_buy'])} 급등:{len(data['top_gainers'])}")
    return data
