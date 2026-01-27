# quant-investment

퀀트 투자 전략 개발 및 백테스팅 프로젝트

[English README](README.md)

## 기술 스택
- **yfinance** - 미국 주가 데이터 수집
- **pykrx** - 한국 주식 데이터 (코스피/코스닥)
- **pandas/numpy** - 데이터 처리
- **matplotlib/seaborn** - 시각화

## 설치

```bash
pip install -r requirements.txt
```

### 버전 확인
```bash
pip show yfinance
# Name: yfinance
# Version: 0.2.63
```

## 프로젝트 구조

```
quant-investment/
├── run.py                        # 메인 진입점 (전략 오케스트레이터)
│
├── scripts/                      # 실행 스크립트
│   ├── screening/                # 종목 스크리닝 스크립트
│   └── live/                     # 실전 거래/봇
│       ├── options_tracker.py    # 옵션 거래량 추적 봇
│       ├── portfolio_sell_checker.py  # 포트폴리오 매도 신호 체커
│       └── global_dual_momentum_2025.py  # 듀얼 모멘텀 전략
│
├── screener/                     # 종목 스크리닝 라이브러리
│   ├── basic_filter.py           # 기본 정보 필터
│   ├── technical_filter.py       # 기술적 지표 필터
│   ├── portfolio_manager.py      # 포트폴리오 관리
│   └── korean/                   # 한국 주식 스크리너
│
├── utils/                        # 유틸리티
│   ├── fetch.py                  # 주가 데이터 수집
│   ├── options_fetch.py          # 옵션 데이터 수집
│   └── ...
│
├── config/                       # 설정 파일
├── data/                         # 데이터 저장소
├── logs/                         # 로그 파일
└── docs/                         # 문서
    └── examples/                 # 예제 및 템플릿
```

## 빠른 시작

### 1. 전략 실행
```bash
# 가상환경 활성화
source venv/bin/activate

# 전략 오케스트레이터 실행
python run.py
```

### 2. 옵션 추적 봇 실행
```bash
# 일회성 체크
python scripts/live/options_tracker.py --once

# 지속적 모니터링 (60초마다)
python scripts/live/options_tracker.py
```

자세한 내용은 [docs/OPTIONS_TRACKER_README.md](docs/OPTIONS_TRACKER_README.md) 참고

### 3. 한국 주식 스크리너 실행
```bash
# 단기/중기 이동평균선 스크리너 (60일, 120일)
python scripts/screening/korean_ma_below.py

# 장기 이동평균선 터치 스크리너 (200일, 240일, 365일)
python scripts/screening/korean_ma_touch.py
```

자세한 내용은 [docs/KOREAN_MA_SCREENER.md](docs/KOREAN_MA_SCREENER.md) 참고

### 4. 새 전략 만들기

1. 템플릿 복사
```bash
cp docs/examples/screening_template.py scripts/screening/my_strategy.py
```

2. 전략 수정
```python
# scripts/screening/my_strategy.py 편집
def run():
    # 여기에 전략 로직 작성
    pass
```

3. `run.py`에서 실행
```bash
python run.py scripts/screening/my_strategy.py
```

## 최근 업데이트

### 옵션 추적 봇 (2025-01)
- NVDA, AAPL, TSLA, AMZN 옵션 거래량 이상 징후 감지
- 5일 평균 대비 2~3배 급증 시 알림
- 자동 데이터 캐싱 및 히스토리 분석

### 글로벌 듀얼 모멘텀 (2025-01)
- 다자산 배분 전략 (주식/채권/현금)
- 모멘텀 기반 자산 스위칭

### 한국 주식 MA 스크리너 (2025-01)
- 코스피 종목 이동평균선 분석
- 60일, 120일, 200일, 240일, 365일선 지원
- 터치/이탈 감지

### 디렉토리 구조 정리 (2025-01)
- `strategies/` → `engine/` (역할에 맞게 이름 변경)
- `my_strategies/` → `scripts/` (실행 스크립트)
- `strategy_templates/` → `docs/examples/` (템플릿 통합)
- 문서화 강화

## 문서

- [Market Calendar](docs/MARKET_CALENDAR_README.md)
- [옵션 추적 봇](docs/OPTIONS_TRACKER_README.md)
- [한국 주식 MA 스크리너](docs/ko/KOREAN_MA_SCREENER.md)
- [코드 품질 리포트](docs/code_quality_report.md)

## 기여하기

새 전략은 `scripts/` 아래 적절한 하위 폴더에 추가해주세요:
- `screening/` - 종목 스크리닝
- `live/` - 실전 거래/봇

## 라이선스

MIT
