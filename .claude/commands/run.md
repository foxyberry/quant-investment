# 스크리닝 실행 명령어 안내

이 작업은 터미널에서 직접 실행하는 것이 효율적입니다.

## 일일 종합 리포트
```bash
python scripts/screening/korean_daily_report.py
```
- 결과: `reports/daily_YYYY-MM-DD.txt` 자동 저장
- 터미널 출력만: `--no-save` 옵션 추가

## 골든크로스/데드크로스
```bash
python scripts/screening/korean_crossover.py
```
- 감지 기간 변경: `--lookback 10`
- 이평선 변경: `--short-ma 5 --long-ma 20`

## 60일/120일선 아래 종목
```bash
python scripts/screening/korean_ma_below.py
```

## 장기 이평선 터치 (200/240/365일)
```bash
python scripts/screening/korean_ma_touch.py
```

---
위 명령어를 터미널에 직접 복사해서 실행하세요.
