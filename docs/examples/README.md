# Examples & Templates

이 폴더는 예제 파일과 전략 템플릿을 포함합니다.

## 템플릿

새 전략을 만들 때 이 템플릿들을 `scripts/` 폴더에 복사하여 사용하세요.

| 파일 | 용도 | 복사 위치 |
|------|------|----------|
| `screening_template.py` | 종목 스크리닝 전략 | `scripts/screening/` |
| `backtesting_template.py` | 백테스팅 전략 | `scripts/backtesting/` |

### 템플릿 사용 방법

```bash
# 스크리닝 전략 생성
cp docs/examples/screening_template.py scripts/screening/my_strategy.py

# 백테스팅 전략 생성
cp docs/examples/backtesting_template.py scripts/backtesting/my_backtest.py

# 전략 실행
python run.py scripts/screening/my_strategy.py
```

## 예제

### Backtrader 예제
- `simple_backtrader_example.py` - 간단한 백트레이더 전략 예제
- `market_calendar_example.py` - 시장 달력 사용 예제

```bash
# 예제 실행
python docs/examples/simple_backtrader_example.py
```

## 참고 문서
- [Backtrader 사용법](../BACKTRADER_README.md)
- [프로젝트 메인 README](../../README.md)
