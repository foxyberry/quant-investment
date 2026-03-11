# #1180 — 시장 내부 지표 + 이벤트 캘린더

## 목표
매크로 모니터에 시장 건강성(Market Breadth) 지표와 주요 이벤트 D-day를 추가한다.

## 데이터 소스 검증 결과

### Market Breadth
- ✅ **상승/하락 종목 비율 (A/D ratio)**: `finance.naver.com/sise/sise_index.naver?code=KOSPI` HTML 스크래핑 (1회 요청)
  - 상한/상승/보합/하락/하한 종목수 직접 제공
- ✅ **52주 신고가/신저가 수**: `fchart.stock.naver.com/sise.nhn` 260일 OHLCV 기반 계산
  - KOSPI ~953종목 × 260일 → ~14초 (동시 20개 워커)
  - 하루 1회 캐시 가능
- ❌ pykrx KRX 함수: HTTP 400 LOGOUT (KRX 봇 차단)

### 이벤트 캘린더
- ✅ **정적 JSON**: FOMC, CPI/고용, 한은 금통위, 옵션만기일 등 연간 일정은 사전 확정
- 외부 API 안정적 소스 없음 → 정적 데이터 + 수동 업데이트 방식 채택

## 구현 범위 (실현 가능 범위)

### Phase 1 (이번 이슈)
1. **A/D ratio** — Naver HTML 1회 스크래핑
2. **이벤트 캘린더** — 정적 JSON (2026 주요 일정)
3. **매크로 페이지 UI** — breadth 카드 + 이벤트 리스트

### Phase 2 (추후 이슈)
- 52주 신고가/신저가 (연산 비용 높음, 별도 캐시 파이프라인 필요)
- KOSPI200 종목 중 20일선 위 비율 (동일 이유)
- 거래대금 확산도

## 변경 파일

| File | Team | Action |
|------|------|--------|
| `api/services/market_breadth_collector.py` | 서버 | 신규: A/D ratio 수집기 |
| `api/services/macro_market_service.py` | 서버 | breadth + events 번들에 추가 |
| `api/schemas/market.py` | 서버 | breadth + events 스키마 추가 |
| `data/market/events_calendar.json` | 데이터 | 2026 주요 이벤트 정적 JSON |
| `web/src/lib/types.ts` | 프론트 | TS 타입 동기화 |
| `web/src/app/[locale]/macro/page.tsx` | 프론트 | breadth 카드 + 이벤트 리스트 |
| `web/messages/{en,ko,zh}.json` | 프론트 | i18n |

## 상세 구현

### Backend Step 1: `market_breadth_collector.py` (신규)

A/D ratio 수집기:
```python
def _fetch_ad_ratio(market="KOSPI") -> dict | None:
    """Scrape advance/decline counts from Naver sise_index page."""
    # GET finance.naver.com/sise/sise_index.naver?code={market}
    # Parse: 상한(limit_up), 상승(advancing), 보합(unchanged), 하락(declining), 하한(limit_down)
    # Return: { advancing, declining, unchanged, limit_up, limit_down, total, ad_ratio }
```

출력 JSON: `data/market/market_breadth_latest.json`
```json
{
  "market": "KOSPI",
  "advancing": 703,
  "declining": 200,
  "unchanged": 24,
  "limit_up": 1,
  "limit_down": 0,
  "total": 928,
  "ad_ratio": 3.515,
  "updated_at": "2026-03-11T07:30:00Z"
}
```

수집 주기: 장중 5분 간격 (investor_flow_collector와 동일 패턴)

### Backend Step 2: `data/market/events_calendar.json` (정적)

```json
[
  { "date": "2026-03-18", "type": "fomc", "title_key": "event_fomc_decision" },
  { "date": "2026-04-10", "type": "us_cpi", "title_key": "event_us_cpi" },
  { "date": "2026-04-17", "type": "kr_monetary", "title_key": "event_kr_monetary" },
  { "date": "2026-03-12", "type": "options_expiry", "title_key": "event_options_expiry" }
]
```

### Backend Step 3: `macro_market_service.py` 확장

- `_get_breadth_snapshot()`: breadth JSON 읽기
- `_get_upcoming_events()`: events JSON에서 향후 14일 이벤트 필터, D-day 계산
- `get_bundle()`에 `breadth` + `events` 필드 추가

### Backend Step 4: `api/schemas/market.py`

```python
class MacroBreadthSnapshot(BaseModel):
    market: str
    advancing: Optional[int] = None
    declining: Optional[int] = None
    unchanged: Optional[int] = None
    total: Optional[int] = None
    ad_ratio: Optional[float] = None
    updated_at: Optional[str] = None

class MacroEvent(BaseModel):
    date: str
    type: str
    title_key: str
    d_day: int  # 0=today, -1=yesterday, 2=in 2 days

# MacroBundleResponse에 추가:
breadth: Optional[MacroBreadthSnapshot] = None
events: Optional[List[MacroEvent]] = None
```

### Frontend Step 5: 타입 + UI

- `types.ts`: MacroBreadthSnapshot, MacroEvent 타입 추가, MacroBundle 확장
- `macro/page.tsx`:
  - Breadth 카드: A/D ratio 게이지바 (상승 비율 vs 하락 비율)
  - Events 리스트: 향후 14일 이벤트, D-day 뱃지 (D-0 = 빨강, D-1~D-3 = 주황, D-4+ = 회색)

### Frontend Step 6: i18n

| Key | en | ko | zh |
|-----|----|----|-----|
| `breadthTitle` | `Market Breadth` | `시장 건강성` | `市场广度` |
| `advancing` | `Advancing` | `상승` | `上涨` |
| `declining` | `Declining` | `하락` | `下跌` |
| `adRatio` | `A/D Ratio` | `등락비` | `涨跌比` |
| `eventsTitle` | `Upcoming Events` | `주요 일정` | `重要事件` |
| `event_fomc_decision` | `FOMC Decision` | `FOMC 결정` | `FOMC 决议` |
| `event_fomc_minutes` | `FOMC Minutes` | `FOMC 의사록` | `FOMC 纪要` |
| `event_us_cpi` | `US CPI Release` | `미국 CPI 발표` | `美国CPI公布` |
| `event_us_employment` | `US Employment Report` | `미국 고용 보고서` | `美国就业报告` |
| `event_kr_monetary` | `BOK Monetary Policy` | `한은 금통위` | `韩国央行货币政策` |
| `event_options_expiry` | `Options Expiry` | `옵션 만기일` | `期权到期日` |
| `event_futures_expiry` | `Futures Expiry` | `선물 만기일` | `期货到期日` |
| `dDay` | `D-{days}` | `D-{days}` | `D-{days}` |
| `dDayToday` | `Today` | `오늘` | `今天` |

## Acceptance Criteria
- [ ] A/D ratio 수집 및 표시 (상승/하락/보합 + 비율)
- [ ] 향후 14일 주요 이벤트 리스트 표시
- [ ] FOMC/금통위 등 D-day 표시
- [ ] i18n (en/ko/zh)
- [ ] 데이터 미가용시 graceful fallback
