# AI 작업 가이드 (Claude Onboarding)

이 문서는 AI가 quant-investment 프로젝트에서 작업하기 전에 읽어야 할 내용과 순서를 정리합니다.

## 1. 필수 문서 읽기 순서

### 1단계: 프로젝트 개요 파악
1. **README.md** - 프로젝트 전체 구조, 스택, 설치 방법, 퀵스타트
2. **docs/BACKTRADER_README.md** - 백테스팅 엔진 사용법 (핵심 기능)

### 2단계: 설정 파일 확인
3. **config/base_config.yaml** - 데이터 경로, API, 로깅, 성능 설정
4. **config/screening_criteria.yaml** - 종목 스크리닝 및 기술적 분석 파라미터

### 3단계: 부가 문서 (필요시)
5. **docs/OPTIONS_TRACKER_README.md** - 옵션 거래량 추적 봇 (옵션 관련 작업시)
6. **docs/MARKET_CALENDAR_README.md** - 마켓 캘린더 유틸 (시간대 관련 작업시)
7. **docs/code_quality_report.md** - 코드 품질 현황

---

## 2. 핵심 코드 파악 순서

### 진입점 (Entry Points)
| 파일 | 용도 | 우선순위 |
|------|------|----------|
| `run.py` | 메인 진입점 (전략 오케스트레이터) | **필수** |
| `options_tracker.py` | 옵션 거래량 추적 봇 | 옵션 작업시 |
| `global_dual_momentum_2025.py` | 듀얼 모멘텀 전략 | 전략 수정시 |

### 백테스팅 엔진 (Core)
| 파일 | 설명 |
|------|------|
| `engine/backtrader_engine.py` | 백테스팅 엔진 래퍼 (핵심) |
| `engine/backtrader_strategy.py` | 기본 전략 클래스들 |
| `engine/bottom_breakout.py` | 바닥 돌파 전략 예제 |

### 스크리너 모듈
| 파일 | 설명 |
|------|------|
| `screener/basic_filter.py` | 기본 정보 필터 (가격, 거래량, 시총) |
| `screener/technical_filter.py` | 기술적 지표 필터 |
| `screener/external_filter.py` | 외부 데이터 필터 |

### 유틸리티
| 파일 | 설명 |
|------|------|
| `utils/fetch.py` | 주가 데이터 수집 (yfinance) |
| `utils/config_manager.py` | 설정 파일 관리 |
| `utils/timezone_utils.py` | 시간대 유틸리티 |

---

## 3. 프로젝트 구조 요약

```
quant-investment/
├── run.py                    # 메인 진입점
├── config/                   # 설정 파일
├── engine/                   # 백트레이더 엔진 (핵심 라이브러리)
│   ├── backtrader_engine.py  # 백테스팅 엔진 래퍼
│   ├── backtrader_strategy.py # 기본 전략 클래스들
│   └── bottom_breakout.py    # 바닥 돌파 전략
├── scripts/                  # 실행 스크립트
│   ├── screening/            # 종목 스크리닝 스크립트
│   └── backtesting/          # 백테스팅 스크립트
├── screener/                 # 종목 스크리닝 라이브러리
├── utils/                    # 유틸리티
├── data/                     # 데이터 저장소
├── logs/                     # 로그
└── docs/                     # 문서
    └── examples/             # 템플릿 및 예제
```

---

## 4. 기술 스택

- **Python 3.13**
- **Backtrader** - 백테스팅 + 실전 거래
- **yfinance** - 주가 데이터 수집
- **ib_insync** - Interactive Brokers 연동
- **pandas/numpy** - 데이터 처리

---

## 5. 실행 환경 확인

```bash
# 가상환경 활성화
source venv/bin/activate

# 의존성 확인
pip list | grep -E "backtrader|yfinance|pandas|numpy"

# 메인 실행
python run.py
```

---

## 6. 작업 유형별 파악 경로

### 새 전략 추가
1. `docs/examples/` 템플릿 확인
2. `scripts/` 구조 파악
3. `run.py`에서 등록 방식 확인

### 스크리닝 조건 수정
1. `config/screening_criteria.yaml` 파악
2. `screener/` 모듈 확인
3. 관련 필터 클래스 수정

### 백테스팅 수정
1. `engine/backtrader_engine.py` 파악
2. `engine/backtrader_strategy.py` 확인
3. 성능 지표 계산 로직 파악

### 옵션 트래커 수정
1. `docs/OPTIONS_TRACKER_README.md` 읽기
2. `options_tracker.py` 코드 확인
3. `utils/` 내 옵션 관련 파일 확인

---

## 7. 주의사항

- `main.py`, `backtrader_main.py`는 레거시 - `run.py` 사용 권장
- 새 전략은 반드시 `scripts/` 하위에 추가
- 데이터 캐시는 `data/cache/`에 저장됨
- 로그는 `logs/quant_investment.log` 확인

---

## 8. 현재 진행 중인 작업

`Todo/1.bot.md` 참조 - 옵션 거래량 이상 징후 감지 봇 구현 계획
