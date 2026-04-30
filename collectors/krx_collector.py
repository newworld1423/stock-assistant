"""
KRX 데이터 수집 모듈 (pykrx 최신 API 기준)
"""

from pykrx import stock
from datetime import datetime, timedelta
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import MARKETS, TOP_VOLUME_COUNT, FOREIGN_TOP_COUNT


def _last_trading_day() -> str:
    today = datetime.now()
    offset = {0: 3, 6: 2}.get(today.weekday(), 1)
    return (today - timedelta(days=offset)).strftime("%Y%m%d")


def get_top_volume(date: str, market: str) -> list:
    try:
        df = stock.get_market_ohlcv(date, market=market)
        if df is None or df.empty:
            return []
        df = df.sort_values("거래량", ascending=False).head(TOP_VOLUME_COUNT)
        result = []
        for ticker in df.index:
            try:
                name = stock.get_market_ticker_name(ticker)
                row  = df.loc[ticker]
                result.append({
                    "ticker":     ticker,
                    "name":       name,
                    "market":     market,
                    "close":      int(row.get("종가", 0)),
                    "volume":     int(row.get("거래량", 0)),
                    "change_pct": round(float(row.get("등락률", 0)), 2),
                })
            except Exception:
                continue
        return result
    except Exception as e:
        print(f"[거래량 수집 오류] {market}: {e}")
        return []


def get_foreign_net_buy(date: str, market: str) -> list:
    try:
        df = stock.get_market_trading_value_by_date(date, date, market)
        if df is None or df.empty:
            return []

        tickers = stock.get_market_ticker_list(date, market=market)
        result  = []

        for ticker in tickers[:FOREIGN_TOP_COUNT]:
            try:
                name  = stock.get_market_ticker_name(ticker)
                fdf   = stock.get_market_trading_value_by_date(date, date, ticker)
                if fdf is None or fdf.empty:
                    continue
                row = fdf.iloc[0]
                foreign_col = next((c for c in fdf.columns if "외국인" in c), None)
                inst_col    = next((c for c in fdf.columns if "기관" in c), None)
                result.append({
                    "ticker":      ticker,
                    "name":        name,
                    "market":      market,
                    "foreign_net": int(row.get(foreign_col, 0)) if foreign_col else 0,
                    "inst_net":    int(row.get(inst_col, 0)) if inst_col else 0,
                    "close":       0,
                    "change_pct":  0,
                })
            except Exception:
                continue

        result.sort(key=lambda x: x["foreign_net"], reverse=True)
        return result[:FOREIGN_TOP_COUNT]
    except Exception as e:
        print(f"[외국인 수집 오류] {market}: {e}")
        return []


def get_top_gainers(date: str, market: str, top_n: int = 10) -> list:
    try:
        df = stock.get_market_ohlcv(date, market=market)
        if df is None or df.empty:
            return []
        df = df[df["거래량"] > 100000]
        df = df.sort_values("등락률", ascending=False).head(top_n)
        result = []
        for ticker in df.index:
            try:
                name = stock.get_market_ticker_name(ticker)
                row  = df.loc[ticker]
                result.append({
                    "ticker":     ticker,
                    "name":       name,
                    "market":     market,
                    "close":      int(row.get("종가", 0)),
                    "change_pct": round(float(row.get("등락률", 0)), 2),
                    "volume":     int(row.get("거래량", 0)),
                })
            except Exception:
                continue
        return result
    except Exception as e:
        print(f"[급등 수집 오류] {market}: {e}")
        return []


def collect_all(date: str = None) -> dict:
    if date is None:
        date = _last_trading_day()

    print(f"[KRX] 수집 날짜: {date}")
    data = {"date": date, "top_volume": [], "foreign_buy": [], "top_gainers": []}

    for market in MARKETS:
        print(f"  → {market} 거래량 상위 수집 중...")
        data["top_volume"]  += get_top_volume(date, market)
        print(f"  → {market} 외국인 순매수 수집 중...")
        data["foreign_buy"] += get_foreign_net_buy(date, market)
        print(f"  → {market} 급등주 수집 중...")
        data["top_gainers"] += get_top_gainers(date, market)

    data["top_volume"].sort(key=lambda x: x["volume"], reverse=True)
    data["top_gainers"].sort(key=lambda x: x["change_pct"], reverse=True)

    print(f"[KRX] 수집 완료 — 거래량:{len(data['top_volume'])} 외국인:{len(data['foreign_buy'])} 급등:{len(data['top_gainers'])}")
    return data


if __name__ == "__main__":
    import json
    print(json.dumps(collect_all(), ensure_ascii=False, indent=2))
