"""
KRX 데이터 수집 모듈 - 컬럼명 한/영 둘 다 대응
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


def _col(df, *candidates):
    """한글/영어 컬럼명 중 존재하는 것 반환"""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def get_top_volume(date: str, market: str) -> list:
    try:
        df = stock.get_market_ohlcv(date, market=market)
        if df is None or df.empty:
            return []

        vol_col    = _col(df, "거래량", "Volume")
        close_col  = _col(df, "종가", "Close")
        change_col = _col(df, "등락률", "Change")

        if not vol_col:
            return []

        df = df.sort_values(vol_col, ascending=False).head(TOP_VOLUME_COUNT)
        result = []
        for ticker in df.index:
            try:
                name = stock.get_market_ticker_name(ticker)
                row  = df.loc[ticker]
                result.append({
                    "ticker":     ticker,
                    "name":       name,
                    "market":     market,
                    "close":      int(row.get(close_col, 0)) if close_col else 0,
                    "volume":     int(row.get(vol_col, 0)),
                    "change_pct": round(float(row.get(change_col, 0)), 2) if change_col else 0,
                })
            except Exception:
                continue
        return result
    except Exception as e:
        print(f"[거래량 수집 오류] {market}: {e}")
        return []


def get_foreign_net_buy(date: str, market: str) -> list:
    try:
        tickers = stock.get_market_ticker_list(date, market=market)
        if not tickers:
            return []

        results = []
        for ticker in tickers[:50]:
            try:
                df = stock.get_market_trading_value_by_date(date, date, ticker)
                if df is None or df.empty:
                    continue
                row = df.iloc[0]
                foreign_col = _col(df, "외국인합계", "외국인", "Foreigner")
                inst_col    = _col(df, "기관합계", "기관", "Institution")
                foreign_net = int(row.get(foreign_col, 0)) if foreign_col else 0
                if foreign_net <= 0:
                    continue
                results.append({
                    "ticker":      ticker,
                    "name":        stock.get_market_ticker_name(ticker),
                    "market":      market,
                    "foreign_net": foreign_net,
                    "inst_net":    int(row.get(inst_col, 0)) if inst_col else 0,
                    "close":       0,
                    "change_pct":  0,
                })
            except Exception:
                continue

        results.sort(key=lambda x: x["foreign_net"], reverse=True)
        return results[:FOREIGN_TOP_COUNT]
    except Exception as e:
        print(f"[외국인 수집 오류] {market}: {e}")
        return []


def get_top_gainers(date: str, market: str, top_n: int = 10) -> list:
    try:
        df = stock.get_market_ohlcv(date, market=market)
        if df is None or df.empty:
            return []

        vol_col    = _col(df, "거래량", "Volume")
        close_col  = _col(df, "종가", "Close")
        change_col = _col(df, "등락률", "Change")

        if not change_col:
            return []

        if vol_col:
            df = df[df[vol_col] > 100000]
        df = df.sort_values(change_col, ascending=False).head(top_n)

        result = []
        for ticker in df.index:
            try:
                name = stock.get_market_ticker_name(ticker)
                row  = df.loc[ticker]
                result.append({
                    "ticker":     ticker,
                    "name":       name,
                    "market":     market,
                    "close":      int(row.get(close_col, 0)) if close_col else 0,
                    "change_pct": round(float(row.get(change_col, 0)), 2),
                    "volume":     int(row.get(vol_col, 0)) if vol_col else 0,
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
