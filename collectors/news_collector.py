"""
뉴스 & 공시 수집 모듈
- 네이버 금융 뉴스 (크롤링)
- DART 공시 (무료 API)
"""

import requests
from datetime import datetime
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

DART_API_KEY = os.getenv("DART_API_KEY", "")  # 없으면 공시 수집 스킵

NAVER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def get_naver_market_news(count: int = 10) -> list[dict]:
    """
    네이버 금융 증권 헤드라인 뉴스 수집
    (RSS 피드 사용 — 크롤링 부담 없음)
    """
    try:
        url = "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258"
        resp = requests.get(url, headers=NAVER_HEADERS, timeout=10)
        resp.encoding = "euc-kr"
        text = resp.text

        # 간단 파싱 (정규식 없이 split 사용)
        results = []
        chunks = text.split('<dt class="articleSubject">')
        for chunk in chunks[1 : count + 1]:
            try:
                title = chunk.split("</a>")[0].split(">")[-1].strip()
                if title:
                    results.append({"title": title})
            except Exception:
                continue

        return results
    except Exception as e:
        print(f"[뉴스 수집 오류] 네이버: {e}")
        return []


def get_dart_disclosures(count: int = 10) -> list[dict]:
    """
    DART 오늘 공시 수집
    API KEY 없으면 빈 리스트 반환
    """
    if not DART_API_KEY:
        return []

    try:
        today = datetime.now().strftime("%Y%m%d")
        url = "https://opendart.fss.or.kr/api/list.json"
        params = {
            "crtfc_key": DART_API_KEY,
            "bgn_de":    today,
            "end_de":    today,
            "page_count": count,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        if data.get("status") != "000":
            return []

        result = []
        for item in data.get("list", [])[:count]:
            result.append({
                "company": item.get("corp_name", ""),
                "title":   item.get("report_nm", ""),
                "time":    item.get("rcept_dt", ""),
            })
        return result
    except Exception as e:
        print(f"[공시 수집 오류] DART: {e}")
        return []


def collect_all() -> dict:
    """전체 뉴스/공시 수집"""
    print("[뉴스] 네이버 금융 뉴스 수집 중...")
    news = get_naver_market_news(10)

    print("[공시] DART 공시 수집 중...")
    disclosures = get_dart_disclosures(10)

    print(f"[뉴스/공시] 완료 — 뉴스:{len(news)} 공시:{len(disclosures)}")
    return {
        "news":         news,
        "disclosures":  disclosures,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(collect_all(), ensure_ascii=False, indent=2))
