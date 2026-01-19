# Backtrader 백테스팅 가이드

이 문서는 quant-investment 프로젝트에서 backtrader 라이브러리를 사용하는 방법을 설명합니다.

[English Documentation](../BACKTRADER_README.md)

## 개요

Backtrader 통합은 다음 기능을 제공하는 종합 백테스팅 프레임워크입니다:
- backtrader의 강력한 엔진을 활용한 돌파 전략 구현
- 기존 스크리닝 및 기술적 분석과 원활한 통합
- 상세한 성과 지표 및 시각화 제공
- 다양한 전략 변형 지원

## 설치

1. backtrader 설치:
```bash
pip install backtrader>=1.9.76
```

2. 기타 의존성은 `requirements.txt`에 포함:
```bash
pip install -r requirements.txt
```

## 파일 구조

```
engine/
├── backtrader_strategy.py      # Backtrader 전략 구현
├── backtrader_engine.py        # Backtrader 엔진 래퍼
└── bottom_breakout.py          # 기존 전략

scripts/
├── screening/                  # 스크리닝 스크립트
└── backtesting/                # 백테스팅 스크립트

docs/examples/
├── backtesting_template.py     # 새 백테스트용 템플릿
└── simple_backtrader_example.py # 간단한 예제
```

## 전략 클래스

### 1. BreakoutStrategy
기존 로직을 구현한 기본 돌파 전략:
- 룩백 기간 내 바닥 가격 식별
- 돌파 레벨(바닥 대비 5% 상승) 돌파 시 매수
- 손절가(바닥 대비 5% 하락) 도달 시 매도

### 2. BreakoutStrategyWithVolume
거래량 확인이 추가된 강화 버전:
- 기본 전략과 동일한 돌파 로직
- 추가 거래량 확인 조건
- 거래량이 10일 평균의 1.5배 이상일 때만 매수

## 사용 예시

### 빠른 시작 - 간단한 예제

```bash
python simple_backtrader_example.py
```

실행 결과:
- 인기 종목 3개 테스트 (AAPL, MSFT, GOOGL)
- 최근 6개월 백테스트 실행
- 각 종목의 인터랙티브 차트 생성
- 다양한 전략 변형 비교

### 전체 통합 - 메인 스크립트

```bash
python scripts/legacy/backtrader_main.py
```

실행 결과:
- 기존 스크리닝 시스템으로 S&P 500 종목 필터링
- 기본 필터 적용 (가격, 거래량, 시가총액)
- 필터링된 종목에 대해 백테스트 실행
- 종합 리포트 및 시각화 생성
- 결과를 CSV 파일로 저장

### 커스텀 백테스팅

```python
from engine.backtrader_engine import BacktraderEngine
from engine.backtrader_strategy import BreakoutStrategy
from screener.technical_criteria import TechnicalCriteria
from datetime import datetime, timedelta

# 엔진 초기화
backtester = BacktraderEngine(initial_capital=100000, commission=0.001)

# 파라미터 설정
technical_criteria = TechnicalCriteria(
    lookback_days=20,
    breakout_threshold=1.05,
    stop_loss_threshold=0.98,
    volume_threshold=1.5
)

# 백테스트 실행
result = backtester.run_backtest(
    symbol='AAPL',
    start_date=datetime.now() - timedelta(days=365),
    end_date=datetime.now(),
    technical_criteria=technical_criteria,
    strategy_class=BreakoutStrategy,
    plot_results=True
)

# 결과 출력
print(f"총 수익률: {result['total_return']:.2%}")
print(f"샤프 비율: {result['sharpe_ratio']:.2f}")
print(f"최대 낙폭: {result['max_drawdown']:.2%}")
```

## 성과 지표

Backtrader 통합은 종합적인 성과 지표를 제공합니다:

### 수익률
- **총 수익률**: 전체 전략 성과
- **바이앤홀드 수익률**: 벤치마크 비교
- **샤프 비율**: 위험 조정 수익률

### 위험 지표
- **최대 낙폭(MDD)**: 최고점에서 최저점까지 최대 하락폭
- **변동성**: 수익률의 표준편차

### 거래 지표
- **총 거래 횟수**: 매수/매도 거래 건수
- **승률**: 수익 거래 비율
- **평균 거래**: 거래당 평균 손익

## 시각화 기능

### 인터랙티브 차트
- 매수/매도 시그널이 포함된 캔들스틱 차트
- 시간에 따른 포트폴리오 가치
- 낙폭 분석
- 거래량 분석

### 성과 리포트
- 전략 비교 테이블
- 위험 지표 요약
- 거래 분석 세부 내역

## 기존 시스템과의 통합

Backtrader 통합은 기존 코드와 원활하게 작동합니다:

1. **스크리닝**: `BasicInfoScreener`를 사용하여 종목 필터링
2. **기술적 분석**: `TechnicalCriteria` 파라미터 사용
3. **데이터 수집**: 기존 `get_historical_data` 함수 사용
4. **설정**: `ConfigManager`로 파라미터 관리

## 설정

모든 파라미터는 기존 YAML 파일을 통해 설정 가능합니다:

```yaml
# config/screening_criteria.yaml
technical_analysis:
  lookback_days: 20
  volume_threshold: 1.5
  breakout_threshold: 1.05
  stop_loss_threshold: 0.95
```

## 고급 기능

### 전략 비교
다양한 전략 변형 비교:
```python
comparison = backtester.compare_strategies(
    symbol='AAPL',
    start_date=start_date,
    end_date=end_date,
    technical_criteria=technical_criteria
)
```

### 배치 백테스팅
여러 종목을 효율적으로 테스트:
```python
results = backtester.batch_backtest(
    symbols=['AAPL', 'MSFT', 'GOOGL'],
    start_date=start_date,
    end_date=end_date,
    technical_criteria=technical_criteria
)
```

### 커스텀 전략 개발
`bt.Strategy`를 상속하여 나만의 전략 생성:
```python
class MyCustomStrategy(bt.Strategy):
    def __init__(self):
        # 커스텀 지표 설정
        pass

    def next(self):
        # 커스텀 로직 구현
        pass
```

## 문제 해결

### 일반적인 문제

1. **데이터 형식**: 데이터에 필수 컬럼이 있는지 확인 (Open, High, Low, Close, Volume)
2. **날짜 범위**: 룩백 기간에 충분한 과거 데이터가 있는지 확인
3. **메모리**: 대용량 데이터셋은 더 많은 메모리 필요; 날짜 범위 축소 고려

### 오류 메시지

- `Missing required column`: 데이터 형식 확인
- `Not enough data`: 날짜 범위 확대 또는 룩백 기간 축소
- `Strategy failed`: 전략 로직 및 파라미터 확인

## 성능 팁

1. **데이터 캐싱**: 기존 캐싱 시스템이 backtrader와 호환됨
2. **병렬 처리**: 여러 백테스트를 병렬로 실행 고려
3. **메모리 관리**: 불필요한 플롯은 닫아서 메모리 확보

## 다음 단계

1. 간단한 예제로 시스템 익히기
2. 필터링된 종목으로 메인 스크립트 실행
3. 다양한 파라미터 실험
4. 연구를 기반으로 커스텀 전략 개발
5. 실전 거래 시스템과 통합

## 지원

문제나 질문이 있으면:
1. backtrader 문서 확인: https://www.backtrader.com/
2. 전략 로직 및 파라미터 검토
3. 간단한 예제로 먼저 테스트
4. 로깅 시스템을 사용하여 디버깅
