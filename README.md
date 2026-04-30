# 📈 주식 비서 — 데이트레이딩 종목 자동 분석 (카카오 버전)

매일 평일 오전 8:10, 전날 시장 데이터를 수집하고 Claude AI가 분석하여
**카카오톡 나에게 보내기**로 데이트레이딩 후보 종목 브리핑을 자동 발송합니다.

---

## ⚙️ 초기 세팅 (순서대로)

### 1단계 — 패키지 설치

```bash
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2단계 — 카카오 개발자 앱 등록 (5분)

1. https://developers.kakao.com 로그인
2. 내 애플리케이션 → 애플리케이션 추가하기
3. 앱 이름 입력 (예: 주식비서)
4. 앱 키 탭에서 REST API 키 복사 → .env에 입력
   ```
   KAKAO_CLIENT_ID=여기에_REST_API_키
   ```
5. 카카오 로그인 메뉴 → 활성화 ON
6. Redirect URI 등록: http://localhost:5000/oauth
7. 동의항목 → 카카오톡 메시지 전송 → 선택 동의

### 3단계 — Anthropic API 키 입력

```
ANTHROPIC_API_KEY=sk-ant-...
```
발급: https://console.anthropic.com

### 4단계 — 카카오 토큰 최초 발급 (딱 1회만)

```bash
python get_kakao_token.py
```

브라우저가 자동으로 열리고 카카오 로그인 후 토큰이 .env에 자동 저장됩니다.
이후 토큰은 자동 갱신되므로 다시 실행할 필요 없어요.

### 5단계 — 테스트 실행

```bash
python main.py
```

카카오톡에 메시지가 오면 성공!

### 6단계 — Railway 배포 (완전 자동화)

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

Railway 대시보드 Variables에 .env 값들 동일하게 입력.
이후 로컬 PC를 꺼도 매일 자동 발송됩니다.

---

## 📁 프로젝트 구조

```
stock-assistant/
├── main.py                  # 메인 실행
├── config.py                # 전체 설정
├── get_kakao_token.py       # 토큰 최초 발급 도우미 (1회만 사용)
├── requirements.txt
├── .env
├── Procfile / railway.toml
│
├── collectors/
│   ├── krx_collector.py     # 국내 주식 (pykrx)
│   ├── global_collector.py  # 미국 지수 / 환율 (yfinance)
│   └── news_collector.py    # 뉴스 / 공시
│
├── analyzer/
│   └── claude_analyzer.py   # Claude API 분석
│
├── notifier/
│   └── kakao_notifier.py    # 카카오 전송 + 토큰 자동 갱신
│
├── scheduler/
│   └── runner.py            # 평일 8:10 자동 실행
│
└── logs/                    # 수집/분석 결과 로그
```

---

## 🔧 커스터마이징 (config.py)

```python
RUN_TIME  = "08:10"               # 실행 시각
MAX_PICKS = 5                     # 최대 추천 종목 수
MARKETS   = ["KOSPI", "KOSDAQ"]  # 분석 시장
```

---

## 💰 비용

| 항목 | 비용 |
|---|---|
| Claude API | 하루 1회 기준 월 약 $0.5 |
| 카카오 나에게 보내기 | 무료 |
| Railway 호스팅 | 무료 플랜 가능 |
| pykrx / yfinance | 무료 |

---

## ⚠️ 주의사항

- 카카오 액세스 토큰(6시간)은 리프레시 토큰으로 자동 갱신됩니다
- 리프레시 토큰은 60일 유효 → 60일마다 get_kakao_token.py 재실행 필요
- Railway 배포 시 KAKAO_REFRESH_TOKEN을 환경변수에 반드시 입력하세요
- 본 분석은 참고용이며 투자 결정은 본인 책임입니다
