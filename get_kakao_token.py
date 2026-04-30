"""
카카오 토큰 최초 발급 도우미 (수동 방식)
실행: python get_kakao_token.py
"""

import requests
import json
import os
import webbrowser
from datetime import datetime, timedelta
from dotenv import load_dotenv, set_key

load_dotenv()

CLIENT_ID     = os.getenv("KAKAO_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "")
REDIRECT_URI  = "https://example.com/oauth"
ENV_FILE      = os.path.join(os.path.dirname(__file__), ".env")


def main():
    print("=" * 55)
    print("  카카오 토큰 발급 도우미")
    print("=" * 55)

    if not CLIENT_ID:
        print("\n[오류] .env 파일에 KAKAO_CLIENT_ID가 없습니다.")
        return

    # Step 1: 브라우저로 카카오 로그인
    auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=talk_message"
    )

    print("\n[Step 1] 아래 URL을 브라우저에 복사해서 여세요:\n")
    print(f"  {auth_url}\n")
    webbrowser.open(auth_url)

    print("[Step 2] 카카오 로그인 후 이동된 주소창을 보면")
    print("  https://example.com/oauth?code=XXXXXXXXXX")
    print("  이런 주소가 나와요. code= 뒤의 값을 복사해주세요.\n")

    code = input("  code 값 붙여넣기 >> ").strip()

    if not code:
        print("[오류] code 값이 없습니다.")
        return

    # Step 3: 토큰 교환
    print("\n토큰 발급 중...")
    data = {
        "grant_type":   "authorization_code",
        "client_id":    CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "code":         code,
    }
    if CLIENT_SECRET:
        data["client_secret"] = CLIENT_SECRET

    try:
        resp   = requests.post("https://kauth.kakao.com/oauth/token", data=data, timeout=10)
        result = resp.json()

        if "error" in result:
            print(f"\n[실패] {result.get('error_description', result)}")
            print("  code가 만료됐을 수 있어요. 다시 실행해서 새 code를 받아주세요.")
            return

        access_token  = result["access_token"]
        refresh_token = result.get("refresh_token", "")
        expires_in    = result.get("expires_in", 21600)

        # .env 저장
        if not os.path.exists(ENV_FILE):
            open(ENV_FILE, "w").close()
        set_key(ENV_FILE, "KAKAO_ACCESS_TOKEN",  access_token)
        set_key(ENV_FILE, "KAKAO_REFRESH_TOKEN", refresh_token)

        # 토큰 캐시 파일 저장
        token_file = os.path.join(os.path.dirname(__file__), "notifier", ".kakao_token.json")
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, "w") as f:
            json.dump({
                "access_token":  access_token,
                "refresh_token": refresh_token,
                "expires_at":    (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
            }, f, indent=2)

        print(f"\n[성공] 토큰 발급 완료! 유효시간: {expires_in // 3600}시간")
        print("  .env 파일과 캐시 파일에 저장됐어요.")
        print("\n이제 실행하세요: python main.py")
        print("=" * 55)

    except Exception as e:
        print(f"\n[오류] {e}")


if __name__ == "__main__":
    main()
