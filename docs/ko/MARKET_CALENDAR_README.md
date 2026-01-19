# 마켓 캘린더 기능

이 프로젝트는 모든 백테스팅과 분석이 유효한 거래일만 사용하도록 종합적인 마켓 캘린더 기능을 포함합니다.

[English Documentation](../MARKET_CALENDAR_README.md)

## 개요

마켓 캘린더 시스템은 다음을 보장합니다:
- ✅ 백테스팅에 거래일만 사용
- ✅ 주말 자동 제외
- ✅ 미국 시장 휴일 자동 제외
- ✅ 유효하지 않은 날짜를 가장 가까운 거래일로 자동 조정
- ✅ 모든 날짜 연산이 시간대 인식 (미국 동부 시간)

## 주요 함수

### 1. 거래일 검증

```python
from utils.timezone_utils import is_trading_day, validate_trading_date

# 해당 날짜가 거래일인지 확인
date = datetime(2024, 1, 15)  # 마틴 루터 킹 주니어 데이
is_trading = is_trading_day(date)  # False 반환

# 날짜 자동 검증 및 조정
adjusted_date = validate_trading_date(date, "종료일")
# 자동으로 이전 거래일로 조정
```

### 2. 거래일 조회

```python
from utils.timezone_utils import get_last_trading_day, get_next_trading_day

# 마지막 거래일 조회
last_trading = get_last_trading_day()  # 마지막 거래일 반환

# 다음 거래일 조회
next_trading = get_next_trading_day()  # 다음 거래일 반환
```

### 3. 백테스팅 날짜 범위

```python
from utils.timezone_utils import get_valid_backtest_dates

# 백테스팅을 위한 유효한 시작일과 종료일 조회
start_date, end_date = get_valid_backtest_dates(days_back=365)
# 365 거래일 이전까지의 유효한 거래일 반환
```

### 4. 기간 내 거래일 조회

```python
from utils.timezone_utils import get_trading_days_between

# 두 날짜 사이의 모든 거래일 조회
trading_days = get_trading_days_between(start_date, end_date)
# 해당 범위의 모든 거래일 리스트 반환
```

## 사용 예시

### 예시 1: 기본 거래일 확인

```python
from datetime import datetime
from utils.timezone_utils import is_trading_day

# 다양한 날짜 테스트
dates_to_test = [
    datetime(2024, 1, 15),  # MLK Day (휴일)
    datetime(2024, 1, 20),  # 토요일
    datetime(2024, 1, 21),  # 일요일
    datetime(2024, 1, 16),  # 일반 화요일
]

for date in dates_to_test:
    is_trading = is_trading_day(date)
    print(f"{date.strftime('%Y-%m-%d %A')}: {'✅ 거래일' if is_trading else '❌ 휴장일'}")
```

### 예시 2: 유효한 날짜로 백테스팅

```python
from utils.timezone_utils import get_valid_backtest_dates

# 유효한 백테스트 날짜 조회
start_date, end_date = get_valid_backtest_dates(days_back=365)

print(f"백테스팅 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
print(f"시작일: {start_date.strftime('%A')}")
print(f"종료일: {end_date.strftime('%A')}")

# 백테스팅에 사용
result = backtester.run_backtest(
    symbol="AAPL",
    start_date=start_date,
    end_date=end_date,
    # ... 기타 파라미터
)
```

### 예시 3: 데이터 수집 시 날짜 검증

```python
from utils.timezone_utils import validate_trading_date

def fetch_stock_data(symbol, end_date):
    # 종료일 검증
    valid_end_date = validate_trading_date(end_date, f"{symbol}의 종료일")

    # 검증된 날짜로 데이터 수집
    data = yfinance.download(symbol, end=valid_end_date)
    return data
```

## 처리되는 미국 시장 휴일

시스템은 다음 미국 시장 휴일을 자동으로 처리합니다:

- 신년 (New Year's Day)
- 마틴 루터 킹 주니어 데이 (Martin Luther King Jr. Day)
- 대통령의 날 (Presidents' Day)
- 성금요일 (Good Friday)
- 현충일 (Memorial Day)
- 준틴스 (Juneteenth)
- 독립기념일 (Independence Day)
- 노동절 (Labor Day)
- 추수감사절 (Thanksgiving Day)
- 크리스마스 (Christmas Day)

## 시간대 처리

모든 날짜는 미국 동부 시간대 (미국 주식 시장 시간대)로 처리됩니다:

```python
from utils.timezone_utils import now, get_current_market_time

# 현재 마켓 시간 조회
current_time = now()  # 미국 동부 시간대의 시간대 인식 datetime 반환
market_time = get_current_market_time()  # now()와 동일
```

## 백테스팅과의 통합

마켓 캘린더는 백테스팅 시스템에 자동으로 통합됩니다:

1. **자동 날짜 검증**: 사용 전 모든 날짜 검증
2. **휴일 인식**: 휴일이나 주말에는 백테스팅 없음
3. **적절한 날짜 범위**: 분석에 충분한 거래일 보장
4. **시간대 일관성**: 모든 날짜가 미국 동부 시간대

## 예제 실행

마켓 캘린더 기능 테스트:

```bash
python docs/examples/market_calendar_example.py
```

다음을 시연합니다:
- 현재 거래일 상태
- 휴일 감지
- 주말 처리
- 날짜 검증 및 조정
- 유효한 백테스트 날짜 생성

## 의존성

마켓 캘린더 기능에 필요한 패키지:

```
pandas_market_calendars>=4.0.0
pytz>=2023.3
```

## 장점

1. **정확성**: 비거래일로 인한 잘못된 시그널 없음
2. **신뢰성**: 휴일과 주말 자동 처리
3. **일관성**: 모든 날짜 연산이 동일한 캘린더 사용
4. **편의성**: 일반적인 날짜 연산을 위한 간단한 함수
5. **시간대 안전성**: 시간대 관련 오류 없음

## 모범 사례

1. **항상 날짜 검증**: 사용자 입력에 `validate_trading_date()` 사용
2. **거래일 함수 사용**: 백테스팅에 `get_valid_backtest_dates()` 사용
3. **거래 상태 확인**: 연산 전 `is_trading_day()` 사용
4. **시간대 처리**: 제공된 시간대 유틸리티를 일관되게 사용
5. **예제로 테스트**: 기능 확인을 위해 예제 스크립트 실행
