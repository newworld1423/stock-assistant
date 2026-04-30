#!/bin/bash
# 주식 비서 초기 세팅 스크립트

echo "=================================================="
echo "  📈 주식 비서 초기 세팅"
echo "=================================================="

# 1. 가상환경 생성
echo "[1/4] 가상환경 생성 중..."
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 패키지 설치
echo "[2/4] 패키지 설치 중..."
pip install -r requirements.txt

# 3. .env 파일 생성
echo "[3/4] .env 파일 생성..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  → .env 파일 생성됨. 직접 편집 필요!"
else
    echo "  → .env 이미 존재함. 스킵."
fi

# 4. 로그 폴더 생성
echo "[4/4] 로그 폴더 생성..."
mkdir -p logs

echo ""
echo "=================================================="
echo "  ✅ 세팅 완료!"
echo "=================================================="
echo ""
echo "다음 단계:"
echo "  1. .env 파일을 열어 API 키 입력"
echo "     - ANTHROPIC_API_KEY"
echo "     - TELEGRAM_BOT_TOKEN"
echo "     - TELEGRAM_CHAT_ID"
echo ""
echo "  2. 텔레그램 봇 만들기:"
echo "     - 텔레그램에서 @BotFather 검색"
echo "     - /newbot 입력 → 봇 이름 지정"
echo "     - 받은 TOKEN을 TELEGRAM_BOT_TOKEN에 입력"
echo "     - @userinfobot 에 메시지 보내면 CHAT_ID 확인 가능"
echo ""
echo "  3. 즉시 테스트 실행:"
echo "     python main.py"
echo ""
echo "  4. 매일 자동 실행 (데몬):"
echo "     python main.py --daemon"
echo ""
echo "  5. Railway 배포:"
echo "     railway up"
echo "=================================================="
