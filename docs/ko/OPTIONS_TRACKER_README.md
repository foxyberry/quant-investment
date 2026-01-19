# 옵션 거래량 추적 봇

`Todo/1.bot.md`의 요구사항에 따라, 주요 종목의 이상 옵션 활동을 모니터링하는 봇입니다.

[English Documentation](../OPTIONS_TRACKER_README.md)

## 기능

- **자동 모니터링**: NVDA, AAPL, TSLA, AMZN 옵션 거래량 추적
- **급등 감지**: 5일 평균 대비 2~3배 거래량 급증 시 알림
- **스마트 캐싱**: API 호출 최소화를 위한 로컬 옵션 데이터 저장
- **히스토리 분석**: 추세 분석을 위한 거래량 이력 구축

## 사용법

### 일회성 체크
```bash
# 가상환경 활성화
source venv/bin/activate

# 일회성 체크 실행
python scripts/live/options_tracker.py --once
```

### 지속적 모니터링
```bash
# 가상환경 활성화
source venv/bin/activate

# 지속적 모니터링 실행 (60초마다 체크)
python scripts/live/options_tracker.py
```

## 알림 레벨

- 🟢 **NORMAL (정상)**: 거래량이 정상 범위 내
- 🟡 **MEDIUM (주의)**: 거래량이 5일 평균의 2배 이상
- 🔴 **HIGH (경고)**: 거래량이 5일 평균의 3배 이상

## 데이터 저장 위치

- **옵션 체인**: `data/options/[SYMBOL]/`
- **거래량 히스토리**: `data/options_volume/`
- **로그**: `logs/options_tracker.log`

## 설정

`scripts/live/options_tracker.py`에서 다음 변수를 수정하세요:
- `TARGET_SYMBOLS`: 모니터링할 종목
- `CHECK_INTERVAL`: 체크 간격 (기본값: 60초)
- `VOLUME_THRESHOLD`: 주의 알림 기준 (기본값: 2.0배)
- `ALERT_THRESHOLD`: 경고 알림 기준 (기본값: 3.0배)

## 아키텍처

트래커는 기존 프로젝트 인프라를 재사용합니다:
- `utils/options_fetch.py`: 옵션 데이터 수집 및 캐싱
- `utils/fetch.py`: 과거 데이터 관리 패턴
- `utils/timezone_utils.py`: 시장 시간 처리

## 출력 예시

```
================================================================================
OPTIONS VOLUME TRACKER - 2025-10-11 23:40:32
================================================================================

Symbol   Volume       vs Avg   P/C Ratio  Alert      Status
----------------------------------------------------------------------
🟢 NVDA   2.0M         1.2x     0.68       NORMAL     정상 활동
🟡 AAPL   590.5K       2.5x     0.60       MEDIUM     거래량이 5일 평균의 2.5배
🟢 TSLA   1.2M         0.9x     0.93       NORMAL     정상 활동
🔴 AMZN   624.4K       3.2x     0.36       HIGH       거래량이 5일 평균의 3.2배
```

## 지표 해석

### P/C Ratio (풋/콜 비율)
- **< 0.7**: 콜 옵션 우세 → 상승 심리
- **0.7 ~ 1.0**: 중립적
- **> 1.0**: 풋 옵션 우세 → 하락 심리 또는 헤지

### 거래량 급등 의미
- **2배 이상**: 시장의 관심 증가, 뉴스나 이벤트 가능성
- **3배 이상**: 매우 이례적인 활동, 대형 트레이더의 포지션 구축 가능성
