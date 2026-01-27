# Backtrader 제거

- **날짜**: 2026-01-27
- **이슈**: 없음
- **브랜치**: `refactor/remove-backtrader`
- **상태**: 계획중

## 목표

사용하지 않는 backtrader 의존성 및 관련 코드 완전 제거, 향후 VectorBT 또는 Backtesting.py로 전환 준비

## 배경

- backtrader는 2020년 이후 개발이 중단됨
- 현재 9개 스크립트 중 1개만 backtrader 사용
- 향후 VectorBT 또는 Backtesting.py로 백테스팅 재구현 예정

## 계획

### Phase 1: 코드 삭제
- [ ] 1단계: `engine/` 폴더 전체 삭제
  - `backtrader_engine.py`
  - `backtrader_strategy.py`
  - `bottom_breakout.py`
- [ ] 2단계: `scripts/backtesting/` 폴더 삭제
  - `momentum_backtest.py`
- [ ] 3단계: `docs/examples/` backtrader 관련 파일 삭제
  - `simple_backtrader_example.py`
  - `backtesting_template.py`

### Phase 2: 문서 정리
- [ ] 4단계: backtrader 관련 문서 삭제
  - `docs/BACKTRADER_README.md`
  - `docs/ko/BACKTRADER_README.md`
- [ ] 5단계: README, CLAUDE.md에서 backtrader 언급 제거

### Phase 3: 의존성 정리
- [ ] 6단계: `requirements.txt`에서 backtrader 제거

### Phase 4: 검증
- [ ] 7단계: 기존 스크립트 동작 확인
  - `python run.py --list`
  - `python scripts/live/portfolio_sell_checker.py`

## 변경 파일

### 삭제 대상

| 파일/폴더 | 사유 |
|----------|------|
| `engine/` (전체) | backtrader 래퍼, 미사용 |
| `scripts/backtesting/` (전체) | backtrader 기반 스크립트 |
| `docs/examples/simple_backtrader_example.py` | backtrader 예제 |
| `docs/examples/backtesting_template.py` | backtrader 템플릿 |
| `docs/BACKTRADER_README.md` | backtrader 문서 |
| `docs/ko/BACKTRADER_README.md` | backtrader 한글 문서 |

### 수정 대상

| 파일 | 변경 내용 |
|------|----------|
| `requirements.txt` | backtrader 의존성 제거 |
| `README.md` | backtrader 언급 제거 |
| `README_KO.md` | backtrader 언급 제거 |
| `CLAUDE.md` | backtrader 언급 제거 |
| `run.py` | backtesting 폴더 참조 제거 (필요시) |

## 기술적 고려사항

### 영향 범위
- `screener/`, `utils/`, `scripts/live/`, `scripts/screening/`에는 영향 없음
- `run.py`에서 `scripts/backtesting/` 참조만 제거

### 향후 계획
- 백테스팅 필요시 VectorBT 또는 Backtesting.py로 재구현
- `engine/` 폴더는 새로운 백테스팅 엔진용으로 재사용 가능

## 결과

(완료 후 작성)
