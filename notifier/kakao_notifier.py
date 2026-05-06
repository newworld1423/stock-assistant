"""
카카오 나에게 보내기 알림 모듈
- 액세스 토큰 자동 갱신 (30일 만료 대응)
- 텍스트 + 링크 템플릿 메시지 지원
"""

import requests
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── 환경변수 ───────────────────────────────────────────────────────────────────
KAKAO_CLIENT_ID     = os.getenv("KAKAO_CLIENT_ID", "")       # REST API 키
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "")   # 보안 키 (선택)
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN", "")   # 리프레시 토큰

# 토큰을 파일로도 저장 (Railway 재시작 대비)
TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".kakao_token.json")

RISK_EMOJI  = {"상": "🔴", "중": "🟡", "하": "🟢"}
STYLE_EMOJI = {
    "갭 상승 추종": "📈", "모멘텀": "🚀",
    "눌림목 반등": "↩️", "돌파 매매": "💥",
}
SENTIMENT_EMOJI = {
    "강한 상승": "🚀", "약한 상승": "📈",
    "보합": "➡️", "약한 하락": "📉", "강한 하락": "💣",
}
OUTLOOK_EMOJI = {"긍정": "✅", "중립": "⚪", "부정": "❌"}


# ── 토큰 관리 ──────────────────────────────────────────────────────────────────

def _load_token() -> dict:
    """저장된 토큰 로드 (파일 우선, 없으면 환경변수)"""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "access_token":  os.getenv("KAKAO_ACCESS_TOKEN", ""),
        "refresh_token": KAKAO_REFRESH_TOKEN,
        "expires_at":    "",
    }


def _save_token(token_data: dict) -> None:
    """토큰을 파일에 저장"""
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[카카오] 토큰 저장 오류: {e}")


def _refresh_access_token(refresh_token: str) -> dict | None:
    """
    리프레시 토큰으로 액세스 토큰 갱신
    Returns: { access_token, refresh_token, expires_in } or None
    """
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type":    "refresh_token",
        "client_id":     KAKAO_CLIENT_ID,
        "refresh_token": refresh_token,
    }
    if KAKAO_CLIENT_SECRET:
        data["client_secret"] = KAKAO_CLIENT_SECRET

    try:
        resp = requests.post(url, data=data, timeout=10)
        result = resp.json()

        if "error" in result:
            print(f"[카카오] 토큰 갱신 실패: {result}")
            return None

        print("[카카오] 액세스 토큰 갱신 성공")
        return result
    except Exception as e:
        print(f"[카카오] 토큰 갱신 오류: {e}")
        return None


def _get_valid_access_token() -> str | None:
    """
    유효한 액세스 토큰 반환
    만료 임박 시 자동 갱신
    """
    token_data = _load_token()
    access_token  = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "") or KAKAO_REFRESH_TOKEN
    expires_at    = token_data.get("expires_at", "")

    # 만료 확인 (1일 여유 두고 갱신)
    needs_refresh = False
    if not access_token:
        needs_refresh = True
    elif expires_at:
        try:
            exp = datetime.fromisoformat(expires_at)
            if datetime.now() >= exp - timedelta(days=1):
                needs_refresh = True
                print("[카카오] 토큰 만료 임박 — 갱신 시작")
        except Exception:
            needs_refresh = True

    if needs_refresh:
        if not refresh_token:
            print("[카카오] 리프레시 토큰 없음 — 수동 재발급 필요")
            return None

        new_tokens = _refresh_access_token(refresh_token)
        if not new_tokens:
            # 갱신 실패 시 기존 토큰으로 일단 시도
            return access_token or None

        expires_in = new_tokens.get("expires_in", 21600)  # 기본 6시간
        new_data = {
            "access_token":  new_tokens["access_token"],
            "refresh_token": new_tokens.get("refresh_token", refresh_token),
            "expires_at":    (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
        }
        _save_token(new_data)

        # 환경변수도 업데이트 (현재 프로세스 내)
        os.environ["KAKAO_ACCESS_TOKEN"] = new_data["access_token"]
        return new_data["access_token"]

    return access_token


# ── 메시지 포맷 ────────────────────────────────────────────────────────────────

def _build_text(result: dict) -> str:
    """분석 결과 → 카카오 텍스트 메시지"""
    if "error" in result:
        return f"⚠️ 분석 오류\n{result.get('error', '')}"

    date = result.get("report_date", "")
    ov   = result.get("market_overview", {})

    us_sent = ov.get("us_sentiment", "")
    kospi   = ov.get("kospi_outlook", "")

    lines = []
    lines.append(f"📊 데이트레이딩 브리핑 {date}")
    lines.append("─" * 24)
    lines.append(
        f"{SENTIMENT_EMOJI.get(us_sent,'➡️')} 미국: {us_sent}  "
        f"{OUTLOOK_EMOJI.get(kospi,'⚪')} 코스피: {kospi}"
    )
    lines.append(f"💡 {ov.get('key_factor','')}")

    caution = ov.get("caution")
    if caution:
        lines.append(f"⚠️ 주의: {caution}")

    theme = result.get("theme_of_day")
    if theme:
        lines.append(f"🎯 오늘의 테마: {theme}")

    picks = result.get("picks", [])
    lines.append(f"\n🔍 후보 종목 ({len(picks)}개)")
    lines.append("─" * 24)

    for p in picks:
        risk  = p.get("risk_level", "중")
        style = p.get("trade_style", "")
        lines.append(
            f"\n{p['rank']}위 {RISK_EMOJI.get(risk,'🟡')} "
            f"{p['name']}({p['ticker']}) {p['market']}"
        )
        close = p.get('close') or 0
        lines.append(f"  {STYLE_EMOJI.get(style,'📌')} {style}")
        lines.append(f"  전일종가 {int(close):,}원")
        lines.append(f"  📝 {p.get('reason') or ''}")
        lines.append(f"  🎯 {p.get('entry_strategy') or ''}")
        lines.append(f"  🛑 손절: {p.get('stop_loss') or ''}")
        lines.append(f"  ✅ 목표1: {p.get('target_1') or ''}  목표2: {p.get('target_2') or ''}")

    avoid = result.get("avoid_today", [])
    if avoid:
        lines.append("\n⛔ 오늘 피할 것")
        for item in avoid:
            lines.append(f"  • {item}")

    lines.append("\n─" * 24)
    lines.append("⚠️ 본 분석은 참고용입니다.")

    return "\n".join(lines)


# ── 전송 ───────────────────────────────────────────────────────────────────────

def send(result: dict) -> bool:
    """카카오 나에게 보내기로 분석 결과 전송"""

    access_token = _get_valid_access_token()
    if not access_token:
        print("[카카오] 액세스 토큰 없음 — 콘솔 출력으로 대체")
        print("=" * 50)
        print(_build_text(result))
        print("=" * 50)
        return False

    text = _build_text(result)

    # 카카오 텍스트 템플릿 (2000자 제한)
    template = {
        "object_type": "text",
        "text":        text[:2000],
        "link": {
            "web_url":        "https://finance.naver.com",
            "mobile_web_url": "https://m.stock.naver.com",
        },
        "button_title": "네이버 증권 열기",
    }

    url  = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/x-www-form-urlencoded",
    }
    data = {"template_object": json.dumps(template, ensure_ascii=False)}

    try:
        resp   = requests.post(url, headers=headers, data=data, timeout=15)
        result_json = resp.json()

        if result_json.get("result_code") == 0:
            print("[카카오] 전송 완료 ✅")
            return True
        else:
            print(f"[카카오] 전송 실패: {result_json}")
            # 토큰 만료 에러(401)면 갱신 후 1회 재시도
            if resp.status_code == 401:
                print("[카카오] 토큰 만료 — 강제 갱신 후 재시도")
                token_data = _load_token()
                new_tokens = _refresh_access_token(
                    token_data.get("refresh_token", KAKAO_REFRESH_TOKEN)
                )
                if new_tokens:
                    new_access = new_tokens["access_token"]
                    _save_token({
                        "access_token":  new_access,
                        "refresh_token": new_tokens.get("refresh_token", ""),
                        "expires_at":    (
                            datetime.now() + timedelta(seconds=new_tokens.get("expires_in", 21600))
                        ).isoformat(),
                    })
                    headers["Authorization"] = f"Bearer {new_access}"
                    resp2 = requests.post(url, headers=headers, data=data, timeout=15)
                    if resp2.json().get("result_code") == 0:
                        print("[카카오] 재시도 전송 완료 ✅")
                        return True
            return False

    except Exception as e:
        print(f"[카카오] 전송 오류: {e}")
        return False


def send_error(message: str) -> None:
    """오류 발생 시 카카오로 알림"""
    send({"error": message})


# ── 최초 토큰 발급 헬퍼 (브라우저 없이 안내) ────────────────────────────────────

def print_auth_guide() -> None:
    """최초 액세스 토큰 발급 안내 출력"""
    if not KAKAO_CLIENT_ID:
        print("❌ KAKAO_CLIENT_ID가 .env에 없습니다.")
        return

    auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_CLIENT_ID}"
        f"&redirect_uri=https://example.com/oauth"
        f"&response_type=code"
        f"&scope=talk_message"
    )
    print("\n" + "=" * 60)
    print("카카오 최초 토큰 발급 절차")
    print("=" * 60)
    print("1. 아래 URL을 브라우저에서 열어 카카오 로그인")
    print(f"\n  {auth_url}\n")
    print("2. 로그인 후 리다이렉트된 URL에서 code= 값 복사")
    print("   예: https://example.com/oauth?code=XXXXXX")
    print("\n3. 아래 명령어 실행 (code= 값 교체):")
    print(f"""
  curl -X POST https://kauth.kakao.com/oauth/token \\
    -d 'grant_type=authorization_code' \\
    -d 'client_id={KAKAO_CLIENT_ID}' \\
    -d 'redirect_uri=https://example.com/oauth' \\
    -d 'code=여기에_code값_입력'
""")
    print("4. 응답에서 access_token, refresh_token 값을 .env에 입력")
    print("   KAKAO_ACCESS_TOKEN=...")
    print("   KAKAO_REFRESH_TOKEN=...")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    if "--guide" in sys.argv:
        print_auth_guide()
    else:
        # 테스트 전송
        dummy = {
            "report_date": "2024-12-16",
            "market_overview": {
                "us_sentiment": "약한 상승",
                "kospi_outlook": "긍정",
                "key_factor": "나스닥 +1.2% 반도체 수혜 기대",
                "caution": "오후 FOMC 의사록 주의",
            },
            "picks": [
                {
                    "rank": 1, "ticker": "005930", "name": "삼성전자",
                    "market": "KOSPI", "close": 75000,
                    "reason": "외국인 1,200억 순매수. HBM 수주 기대감.",
                    "entry_strategy": "9:05 이후 75,000 지지 확인 후 매수",
                    "stop_loss": "73,500원 (-2.0%)",
                    "target_1": "76,500원", "target_2": "78,000원",
                    "risk_level": "하", "trade_style": "모멘텀",
                }
            ],
            "avoid_today": ["코스닥 소형주 — 테마 없이 변동성만 높음"],
            "theme_of_day": "AI 반도체",
        }
        send(dummy)
