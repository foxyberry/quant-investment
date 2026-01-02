# quant-investment

퀀트 투자 전략 개발 및 백테스팅 프로젝트

## Stack
- **Backtrader** - 백테스팅 + 실전 거래
- **yfinance** - 주가 데이터 수집
- **ib_insync** - Interactive Brokers 연동
- **pandas/numpy** - 데이터 처리

## Installation

### 기본 패키지
```bash
pip install 'backtrader[plotting]' matplotlib pandas numpy
pip install --upgrade yfinance --no-cache-dir
pip install lxml
```

### 실전 거래용
```bash
pip install ib_insync
```

### 버전 확인
```bash
pip show yfinance
# Name: yfinance
# Version: 0.2.63
```

## Project Structure

```
quant-investment/
├── run.py                        # 메인 진입점 (전략 오케스트레이터)
├── main.py                       # 레거시 스크리닝 (run.py 사용 권장)
├── backtrader_main.py            # 레거시 백테스팅 (run.py 사용 권장)
│
├── global_dual_momentum_2025.py  # 글로벌 듀얼 모멘텀 전략
├── options_tracker.py            # 옵션 거래량 추적 봇
│
├── my_strategies/                # 사용자 커스텀 전략 (여기에 새 전략 추가)
│   ├── screening/                # 종목 스크리닝 전략
│   ├── backtesting/              # 백테스팅 전략
│   ├── optimization/             # 파라미터 최적화 전략
│   └── live/                     # 실전 거래 전략
│
├── strategies/                   # 백트레이더 엔진 및 기본 전략
│   ├── backtrader_engine.py      # 백테스팅 엔진 (핵심)
│   ├── backtrader_strategy.py    # 기본 전략 클래스
│   └── bottom_breakout.py        # 바닥 돌파 전략 예제
│
├── screener/                     # 종목 스크리닝 모듈
│   ├── basic_filter.py           # 기본 정보 필터
│   ├── technical_filter.py       # 기술적 지표 필터
│   └── ...
│
├── utils/                        # 유틸리티
│   ├── fetch.py                  # 주가 데이터 수집
│   ├── options_fetch.py          # 옵션 데이터 수집
│   └── ...
│
├── strategy_templates/           # 전략 템플릿
│   ├── screening_template.py
│   └── backtesting_template.py
│
├── data/                         # 데이터 저장소
├── logs/                         # 로그 파일
├── results/                      # 백테스팅 결과
└── docs/                         # 문서
    ├── examples/                 # 예제 파일
    └── ...
```

## Quick Start

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
python options_tracker.py --once

# 지속적 모니터링 (60초마다)
python options_tracker.py
```

자세한 내용은 [OPTIONS_TRACKER_README.md](OPTIONS_TRACKER_README.md) 참고

### 3. 새 전략 만들기

1. 템플릿 복사
```bash
cp strategy_templates/screening_template.py my_strategies/screening/my_strategy.py
```

2. 전략 수정
```python
# my_strategies/screening/my_strategy.py 편집
def run():
    # 여기에 전략 로직 작성
    pass
```

3. `run.py`에서 실행

## Recent Updates

### 옵션 추적 봇 (2025-01)
- NVDA, AAPL, TSLA, AMZN 옵션 거래량 이상 징후 감지
- 5일 평균 대비 2~3배 급증 시 알림
- 자동 데이터 캐싱 및 히스토리 분석

### 글로벌 듀얼 모멘텀 (2025-01)
- 다자산 배분 전략 (주식/채권/현금)
- 모멘텀 기반 자산 스위칭

### 전략 구조 개선
- `my_strategies/` 폴더 조직화
- 전략 템플릿 추가
- 문서화 강화

## Documentation

- [Backtrader 사용법](docs/BACKTRADER_README.md)
- [Market Calendar](docs/MARKET_CALENDAR_README.md)
- [옵션 추적 봇](OPTIONS_TRACKER_README.md)
- [코드 품질 리포트](docs/code_quality_report.md)

## Contributing

새 전략은 `my_strategies/` 아래 적절한 하위 폴더에 추가해주세요:
- `screening/` - 종목 스크리닝
- `backtesting/` - 백테스팅
- `optimization/` - 파라미터 최적화
- `live/` - 실전 거래

## License

MIT
