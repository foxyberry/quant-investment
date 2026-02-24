# Condition Research Guide (Issue #487)

목표: 등록된 모든 조건을 나열하고, 코드 기반 파라미터 default와 인터넷 근거(정의/사용 시점/해석/주의점)를 한 문서에 연결합니다.

- 조건 수: **156개**
- 파라미터/기본값 추출 방식: `screener/conditions/*.py`의 `@register_condition` AST 파싱
- 근거는 지표군 단위로 매핑 (`sources` 컬럼 태그 참조)

## Source Index
- **S_RSICORE**: [RSI (정의/해석/파라미터)](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi)
- **S_MACD**: [MACD (정의/신호선 교차)](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-moving-average-convergence-divergence-oscillator)
- **S_STOCH**: [Stochastic Oscillator](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/stochastic-oscillator-fast-slow-and-full)
- **S_WILLR**: [Williams %R](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/williams-r)
- **S_CCI**: [Commodity Channel Index (CCI)](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/commodity-channel-index-cci)
- **S_MFI**: [Money Flow Index (MFI)](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/money-flow-index-mfi)
- **S_BB**: [Bollinger BandWidth / %B](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/bollinger-bandwidth)
- **S_ATR**: [ATR (Average True Range)](https://www.britannica.com/money/average-true-range-indicator)
- **S_ADX**: [ADX / Directional Movement](https://www.britannica.com/money/average-directional-index-adx)
- **S_AROON**: [Aroon / Aroon Oscillator](https://www.investopedia.com/terms/a/aroon.asp)
- **S_ICHI**: [Ichimoku Cloud](https://www.investopedia.com/terms/i/ichimoku-cloud.asp)
- **S_VWAP**: [VWAP](https://www.investopedia.com/terms/v/vwap.asp)
- **S_OBV**: [On-Balance Volume (OBV)](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/on-balance-volume-obv)
- **S_CHAIKIN**: [Chaikin Money Flow / Oscillator](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/chaikin-money-flow-cmf)
- **S_DONCHIAN**: [Donchian Channel](https://www.investopedia.com/terms/d/donchianchannels.asp)
- **S_KELTNER**: [Keltner Channel](https://www.investopedia.com/terms/k/keltnerchannel.asp)
- **S_PARABOLIC**: [Parabolic SAR](https://www.investopedia.com/terms/p/parabolicindicator.asp)
- **S_VAL**: [P/E 정의 (규제기관 용어집)](https://www.investor.gov/introduction-investing/investing-basics/glossary/price-earnings-pe-ratio)
- **S_FACTORS**: [Fama/French Data Library (팩터 정의/구성)](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)
- **S_MOM**: [Momentum Profitability (Jegadeesh & Titman, 1993)](https://www.sciencedirect.com/science/article/abs/pii/0304405X93900235)
- **S_PEAD**: [Post-Earnings-Announcement Drift (Bernard & Thomas, 1989)](https://www.sciencedirect.com/science/article/abs/pii/0304405X89900489)
- **S_ACCRUALS**: [Accrual Anomaly (Sloan, 1996)](https://www.sciencedirect.com/science/article/abs/pii/016541019600010X)
- **S_SEASONAL**: [Day-of-Week Effect 개요](https://en.wikipedia.org/wiki/Day_of_the_week_effect)
- **S_ISSUANCE**: [Share issuance and expected returns (Pontiff & Woodgate, 2008)](https://www.sciencedirect.com/science/article/abs/pii/S0304405X08000064)
- **S_SHORT**: [Short Interest Ratio 개요](https://www.investopedia.com/terms/s/shortinterestratio.asp)
- **S_INSIDER**: [Insider Trading basics (SEC)](https://www.sec.gov/about/reports-publications/investorpubsinsiderhtm)

## Condition Catalog

| key | code definition(description) | category | params(default) | 파라미터 설정(초기) | 해석 방법 | 주의점 | sources |
|---|---|---|---|---|---|---|---|
| `above_ma` | Price above moving average | `movingAverage` | `period`(int)=20, `min_distance_pct`(float)=0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `accruals_ratio` | Accruals ratio from income and cash flow | `quality` | `max_ratio`(float)=0.1 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` `S_ACCRUALS` |
| `ad_line_trend` | Accumulation/distribution line trend | `moneyflow` | `lookback_days`(int)=20 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_OBV` |
| `adx_trend_strength` | ADX trend strength filter | `momentum` | `period`(int)=14, `min_adx`(float)=25.0, `di_direction`(str)=any | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_ADX` |
| `altman_zscore` | Altman Z-Score bankruptcy risk filter | `Fundamental` | `min_zscore`(float)=2.5, `max_zscore`(float)=None | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `analyst_revision_1m` | One-month analyst estimate revision | `fundamental` | `min_revision_pct`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `analyst_revision_3m` | Three-month analyst estimate revision | `fundamental` | `min_revision_pct`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `aroon_oscillator_signal` | Aroon up-down oscillator filter | `oscillator` | `period`(int)=25, `min_oscillator`(float)=30.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 극단값(과매수/과매도)에 가까울수록 반전 신호 강도↑ | 강한 단방향 추세에서는 역추세 신호가 장기간 실패 가능 | `S_AROON` |
| `aroon_trend_signal` | Aroon trend strength signal | `momentum` | `period`(int)=25, `min_aroon`(float)=70, `direction`(str)=up | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_AROON` |
| `asset_growth_rate` | Total asset growth rate | `quality` | `max_growth_pct`(float)=15.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `asset_turnover_ratio` | Revenue to total assets turnover ratio | `fundamental` | `min_ratio`(float)=0.5 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `atr_expansion_breakout` | ATR expansion and price breakout | `risk` | `atr_period`(int)=14, `atr_multiplier`(float)=1.2, `breakout_lookback`(int)=20 | 기본값으로 시작 후 민감도(±20~30%) 테스트 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_ATR` |
| `atr_percentile_filter` | ATR percentile within lookback | `risk` | `atr_period`(int)=14, `lookback_days`(int)=120, `max_percentile`(float)=80.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_ATR` |
| `avg_trading_value` | N-day average trading value >= threshold | `volume` | `lookback_days`(int)=20, `min_value`(float)=1500000000 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 거래량/자금흐름 지표는 가격 대비 선행/확인 신호로 사용 | 저유동성 구간에서 지표 안정성 저하 | `S_FACTORS` |
| `below_ma` | Price below moving average | `movingAverage` | `period`(int)=20, `max_distance_pct`(float)=0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `beta_to_benchmark` | Rolling beta versus benchmark | `risk` | `lookback_days`(int)=60, `max_beta`(float)=1.2 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_FACTORS` |
| `bollinger_percent_b` | Price position within Bollinger bands | `oscillator` | `period`(int)=20, `std_mult`(float)=2.0, `min_percent_b`(float)=0.0, `max_percent_b`(float)=1.0 | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_BB` |
| `bollinger_squeeze_breakout` | Low BB width followed by upper band breakout | `oscillator` | `period`(int)=20, `std_mult`(float)=2.0, `max_width_pct`(float)=10.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_BB` |
| `bollinger_width` | BB width contraction | `accumulation` | `max_width_pct`(float)=15.0, `period`(int)=20, `std_dev`(float)=2.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 거래량/자금흐름 지표는 가격 대비 선행/확인 신호로 사용 | 저유동성 구간에서 지표 안정성 저하 | `S_BB` |
| `book_to_market_ratio` | Book value divided by market cap | `fundamental` | `min_ratio`(float)=0.3 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `bottom_breakout` | N-day low breakout | `breakout` | `lookback_days`(int)=20, `breakout_pct`(float)=5.0 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `breakout_with_volume` | Breakout confirmed by volume spike | `breakout` | `lookback_days`(int)=20, `breakout_pct`(float)=5.0, `volume_ratio`(float)=1.5, `volume_avg_days`(int)=10, `fresh_only`(bool)=True | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `buyback_yield_filter` | Minimum buyback yield | `fundamental` | `min_yield_pct`(float)=1.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `calmar_ratio_filter` | Calmar ratio filter | `risk` | `lookback_days`(int)=252, `min_calmar`(float)=0.5 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_FACTORS` |
| `cash_conversion_ratio` | Operating cash flow over net income | `fundamental` | `min_ratio`(float)=0.8 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `cashflow_to_debt_ratio` | Operating cash flow to debt ratio | `fundamental` | `min_ratio`(float)=0.2 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `cci_overbought_oversold` | CCI threshold filter | `momentum` | `period`(int)=20, `mode`(str)=oversold, `threshold`(float)=100 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 극단값(과매수/과매도)에 가까울수록 반전 신호 강도↑ | 강한 단방향 추세에서는 역추세 신호가 장기간 실패 가능 | `S_CCI` |
| `chaikin_money_flow_signal` | CMF threshold signal | `moneyflow` | `period`(int)=20, `min_cmf`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 거래량/자금흐름 지표는 가격 대비 선행/확인 신호로 사용 | 저유동성 구간에서 지표 안정성 저하 | `S_CHAIKIN` |
| `chaikin_oscillator_signal` | Chaikin oscillator above threshold | `moneyflow` | `fast_period`(int)=3, `slow_period`(int)=10, `min_value`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 극단값(과매수/과매도)에 가까울수록 반전 신호 강도↑ | 강한 단방향 추세에서는 역추세 신호가 장기간 실패 가능 | `S_CHAIKIN` |
| `correlation_to_benchmark` | Rolling correlation versus benchmark | `risk` | `lookback_days`(int)=60, `max_corr`(float)=0.8 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_FACTORS` |
| `current_ratio` | Current ratio (liquidity) filter | `Fundamental` | `min_ratio`(float)=1.0, `max_ratio`(float)=3.0 | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `day_of_week_seasonality` | Average weekday return effect | `time` | `target_weekday`(int)=0, `min_avg_return_pct`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 이벤트·캘린더 효과는 시기 의존성이 커 구간별 분리 해석 필요 | 거래비용·슬리피지 반영 시 유의미성 약화 가능 | `S_SEASONAL` |
| `death_cross_50_200` | 50MA crossing below 200MA | `movingAverage` | `lookback_days`(int)=5 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `debt_service_coverage_ratio` | Operating income over debt service | `fundamental` | `min_ratio`(float)=1.2 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `debt_to_equity` | Debt-to-Equity ratio filter | `Fundamental` | `min_de`(float)=None, `max_de`(float)=100.0 | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `distance_from_200d_high` | Distance below 200-day high | `price` | `lookback_days`(int)=200, `max_distance_pct`(float)=15.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_FACTORS` |
| `distance_from_52w_high` | Distance below 52-week high | `price` | `lookback_days`(int)=252, `max_distance_pct`(float)=10.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_MOM` `S_FACTORS` |
| `distance_from_52w_low` | Distance from 252-day low | `price` | `lookback_days`(int)=252, `max_distance_pct`(float)=30.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_MOM` `S_FACTORS` |
| `dividend_growth_5y` | 5-year dividend CAGR | `fundamental` | `min_growth_pct`(float)=3.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `dividend_yield` | Dividend yield percentage filter | `Fundamental` | `min_yield`(float)=3.0, `max_yield`(float)=None | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `dmi_directional_cross` | +DI crosses above -DI | `momentum` | `period`(int)=14, `lookback_days`(int)=5 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_ADX` |
| `donchian_channel_breakout` | Breakout above Donchian upper band | `breakout` | `lookback_days`(int)=20 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_DONCHIAN` |
| `downside_volatility_filter` | Annualized downside volatility filter | `risk` | `lookback_days`(int)=60, `max_downside_vol_pct`(float)=20.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_FACTORS` |
| `drawdown_from_high` | Drop % from N-day rolling high | `price` | `lookback_days`(int)=120, `min_drop_pct`(float)=20.0, `price_field`(str)=high | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_FACTORS` |
| `dso_trend_filter` | Days Sales Outstanding deterioration trend filter | `Fundamental` | `lookback_years`(int)=1, `min_dso_increase_pct`(float)=5.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `earnings_stability_score` | Earnings stability based on coefficient of variation | `fundamental` | `lookback_years`(int)=5, `max_cv`(float)=0.35 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `earnings_surprise_filter` | Quarterly earnings surprise threshold | `event` | `min_surprise_pct`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 이벤트·캘린더 효과는 시기 의존성이 커 구간별 분리 해석 필요 | 거래비용·슬리피지 반영 시 유의미성 약화 가능 | `S_PEAD` |
| `earnings_yield` | Earnings yield (E/P) percentage filter | `Fundamental` | `min_yield`(float)=8.0, `max_yield`(float)=None | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `ebit_ev` | EBIT / Enterprise Value yield filter | `Fundamental` | `min_ebit_ev`(float)=10.0, `max_ebit_ev`(float)=None | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `ema_cross` | EMA cross signal | `momentum` | `fast_period`(int)=12, `slow_period`(int)=26, `lookback_days`(int)=5, `direction`(str)=bullish | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `ema_slope` | EMA slope over lookback | `momentum` | `period`(int)=20, `lookback_days`(int)=5, `min_slope_pct`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `eps_cagr_3y` | 3-year EPS CAGR | `fundamental` | `min_cagr_pct`(float)=5.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `eps_growth_yoy` | Year-over-year EPS growth | `fundamental` | `min_growth_pct`(float)=5.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `ev_to_ebitda_ratio` | Enterprise value to EBITDA ratio | `fundamental` | `max_ratio`(float)=12.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `ev_to_sales_ratio` | Enterprise value to sales ratio | `fundamental` | `max_ratio`(float)=4.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `fcf_yield` | Free Cash Flow yield filter | `Fundamental` | `min_fcf_yield`(float)=5.0, `max_fcf_yield`(float)=None | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `free_cash_flow_margin` | Free cash flow margin | `fundamental` | `min_margin_pct`(float)=5.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `fresh_breakout` | First-time breakout detection | `breakout` | `lookback_days`(int)=20, `breakout_pct`(float)=5.0 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `gap_down_exhaustion` | Large down-gap exhaustion signal | `price` | `min_gap_down_pct`(float)=2.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 이벤트·캘린더 효과는 시기 의존성이 커 구간별 분리 해석 필요 | 거래비용·슬리피지 반영 시 유의미성 약화 가능 | `S_FACTORS` |
| `gap_up_breakaway` | Gap-up breakout using previous high | `price` | `min_gap_pct`(float)=1.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 이벤트·캘린더 효과는 시기 의존성이 커 구간별 분리 해석 필요 | 거래비용·슬리피지 반영 시 유의미성 약화 가능 | `S_FACTORS` |
| `golden_cross_50_200` | 50MA crossing above 200MA | `movingAverage` | `lookback_days`(int)=5 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `gross_margin` | Gross profit margin | `fundamental` | `min_margin_pct`(float)=20.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `gross_profitability` | Gross profit to total assets | `quality` | `min_ratio`(float)=0.2 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `ichimoku_cloud_breakout` | Close above cloud upper | `momentum` | `conversion_period`(int)=9, `base_period`(int)=26, `span_b_period`(int)=52 | 기본값으로 시작 후 민감도(±20~30%) 테스트 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_ICHI` |
| `ichimoku_tenkan_kijun_cross` | Tenkan crosses above Kijun | `momentum` | `conversion_period`(int)=9, `base_period`(int)=26, `lookback_days`(int)=5 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_ICHI` |
| `insider_net_buying` | Insider net buying ratio | `fundamental` | `min_net_buying_pct`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` `S_INSIDER` |
| `interest_coverage_ratio` | EBIT over interest expense | `fundamental` | `min_ratio`(float)=3.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `intraday_return_filter` | Intraday return filter | `risk` | `min_intraday_return_pct`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 이벤트·캘린더 효과는 시기 의존성이 커 구간별 분리 해석 필요 | 거래비용·슬리피지 반영 시 유의미성 약화 가능 | `S_FACTORS` |
| `inventory_turnover_ratio` | COGS to inventory turnover ratio | `fundamental` | `min_ratio`(float)=3.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `keltner_channel_breakout` | Breakout above EMA + ATR band | `breakout` | `ema_period`(int)=20, `atr_period`(int)=20, `atr_multiplier`(float)=2.0 | 기본값으로 시작 후 민감도(±20~30%) 테스트 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_KELTNER` |
| `linear_regression_angle_filter` | Linear regression angle threshold | `momentum` | `lookback_days`(int)=60, `min_angle_deg`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_FACTORS` |
| `linear_regression_r2_filter` | Linear regression R2 threshold | `momentum` | `lookback_days`(int)=60, `min_r2`(float)=0.5 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_FACTORS` |
| `linear_regression_slope_filter` | Linear regression slope threshold | `momentum` | `lookback_days`(int)=60, `min_slope`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `ma_cross_down` | Death cross (short MA crosses below long MA) | `movingAverage` | `short_period`(int)=20, `long_period`(int)=60, `lookback_days`(int)=5 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `ma_cross_up` | Golden cross (short MA crosses above long MA) | `movingAverage` | `short_period`(int)=5, `long_period`(int)=20, `lookback_days`(int)=5 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `ma_ribbon_alignment` | Short>Mid>Long MA alignment | `movingAverage` | `short_period`(int)=20, `mid_period`(int)=50, `long_period`(int)=200 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `ma_touch` | Price near moving average | `movingAverage` | `period`(int)=120, `threshold`(float)=0.02 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `macd_histogram_slope` | MACD histogram slope | `momentum` | `fast_period`(int)=12, `slow_period`(int)=26, `signal_period`(int)=9, `lookback_days`(int)=3, `min_slope`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_MACD` |
| `macd_signal_cross` | MACD line crossing signal line | `momentum` | `fast_period`(int)=12, `slow_period`(int)=26, `signal_period`(int)=9, `lookback_days`(int)=5, `direction`(str)=bullish | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_MACD` |
| `max_drawdown_window_filter` | Window max drawdown filter | `risk` | `lookback_days`(int)=120, `max_drawdown_pct`(float)=20.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_FACTORS` |
| `max_price` | Stock price <= threshold | `price` | `max_price`(float)=100000 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_FACTORS` |
| `min_price` | Stock price >= threshold | `price` | `min_price`(float)=5000 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_FACTORS` |
| `min_volume` | Volume >= threshold | `volume` | `min_volume`(int)=100000 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 거래량/자금흐름 지표는 가격 대비 선행/확인 신호로 사용 | 저유동성 구간에서 지표 안정성 저하 | `S_FACTORS` |
| `momentum_12_1` | 12-month momentum excluding recent 1 month | `momentum` | `lookback_months`(int)=12, `skip_recent_months`(int)=1, `min_return_pct`(float)=20.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_MOM` `S_FACTORS` |
| `money_flow_index_signal` | MFI threshold signal | `momentum` | `period`(int)=14, `mode`(str)=oversold, `oversold`(float)=20, `overbought`(float)=80 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_MFI` |
| `month_of_year_seasonality` | Average return for target month | `time` | `target_month`(int)=1, `min_avg_return_pct`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 이벤트·캘린더 효과는 시기 의존성이 커 구간별 분리 해석 필요 | 거래비용·슬리피지 반영 시 유의미성 약화 가능 | `S_SEASONAL` |
| `natr_filter` | Normalized ATR filter | `risk` | `period`(int)=14, `max_natr_pct`(float)=5.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_ATR` |
| `net_debt_to_ebitda` | Net debt divided by EBITDA | `fundamental` | `max_ratio`(float)=3.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `net_margin` | Net income margin | `fundamental` | `min_margin_pct`(float)=5.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `net_share_issuance_filter` | Limit net share issuance | `fundamental` | `max_issuance_pct`(float)=1.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` `S_ISSUANCE` |
| `obv_divergence` | Price flat + OBV rising (accumulation signal) | `accumulation` | `price_max_range_pct`(float)=5.0, `obv_min_change_pct`(float)=5.0, `period`(int)=20 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 거래량/자금흐름 지표는 가격 대비 선행/확인 신호로 사용 | 저유동성 구간에서 지표 안정성 저하 | `S_OBV` |
| `obv_trend` | On-Balance Volume trend direction | `accumulation` | `direction`(str)=up, `lookback`(int)=20 | 방향형: 전략 포지션과 일치 필요 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_OBV` |
| `opening_range_breakout` | Close breaks previous day range | `price` | `direction`(str)=up | 방향형: 전략 포지션과 일치 필요 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `operating_margin` | Operating income margin | `fundamental` | `min_margin_pct`(float)=10.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `overnight_return_filter` | Previous close to current open return filter | `time` | `min_overnight_return_pct`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 이벤트·캘린더 효과는 시기 의존성이 커 구간별 분리 해석 필요 | 거래비용·슬리피지 반영 시 유의미성 약화 가능 | `S_FACTORS` |
| `parabolic_sar_flip` | Bullish SAR flip within lookback | `momentum` | `lookback_days`(int)=5, `af_step`(float)=0.02, `af_max`(float)=0.2 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_PARABOLIC` |
| `payout_ratio_filter` | Dividend payout ratio | `fundamental` | `max_payout_pct`(float)=70.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `pb_ratio` | Price-to-Book ratio filter | `Fundamental` | `min_pb`(float)=None, `max_pb`(float)=1.5, `exclude_negative_bv`(bool)=True | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `pcf_ratio` | Price-to-Cash-Flow ratio filter | `Fundamental` | `min_pcf`(float)=None, `max_pcf`(float)=10.0 | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `pe_ratio` | Price-to-Earnings ratio filter | `Fundamental` | `min_pe`(float)=None, `max_pe`(float)=15.0 | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `peg_ratio` | Price/Earnings-to-Growth ratio filter | `Fundamental` | `min_peg`(float)=None, `max_peg`(float)=1.0 | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `piotroski_fscore` | Piotroski F-Score (0-9) financial strength | `Fundamental` | `min_score`(int)=7, `max_score`(int)=None | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `pivot_point_breakout` | Breakout above/below classic pivot | `price` | `direction`(str)=up | 방향형: 전략 포지션과 일치 필요 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `post_earnings_drift` | Post-earnings drift threshold | `event` | `min_return_pct`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 이벤트·캘린더 효과는 시기 의존성이 커 구간별 분리 해석 필요 | 거래비용·슬리피지 반영 시 유의미성 약화 가능 | `S_PEAD` |
| `ppo_signal_cross` | PPO line crossing signal line | `oscillator` | `fast_period`(int)=12, `slow_period`(int)=26, `signal_period`(int)=9, `lookback_days`(int)=5 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_MACD` |
| `pre_earnings_drift` | Pre-earnings drift threshold | `event` | `min_return_pct`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 이벤트·캘린더 효과는 시기 의존성이 커 구간별 분리 해석 필요 | 거래비용·슬리피지 반영 시 유의미성 약화 가능 | `S_PEAD` |
| `price_change` | Price change over N days | `price` | `min_change_pct`(float)=None, `max_change_pct`(float)=None, `days`(int)=1 | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_FACTORS` |
| `price_flat` | Price consolidation (low volatility) | `accumulation` | `max_range_pct`(float)=10.0, `period`(int)=20 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 거래량/자금흐름 지표는 가격 대비 선행/확인 신호로 사용 | 저유동성 구간에서 지표 안정성 저하 | `S_FACTORS` |
| `price_range` | Stock price within range | `price` | `min_price`(float)=0, `max_price`(float)=999999 | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_FACTORS` |
| `price_to_tangible_book` | Market cap to tangible book ratio | `fundamental` | `max_ratio`(float)=3.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `ps_ratio` | Price-to-Sales ratio filter | `Fundamental` | `min_ps`(float)=None, `max_ps`(float)=2.0 | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `quality_score` | Composite quality score from ROA, gross profitability and accruals | `quality` | `min_score`(float)=0.5 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `receivables_turnover_ratio` | Revenue to receivables turnover ratio | `fundamental` | `min_ratio`(float)=4.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `relative_strength_vs_benchmark` | Stock return minus benchmark return | `momentum` | `lookback_days`(int)=63, `min_excess_return_pct`(float)=5.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_MOM` `S_FACTORS` |
| `relative_volume_percentile` | Current volume percentile within lookback | `volume` | `lookback_days`(int)=60, `min_percentile`(float)=70.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `resistance_breakout` | N-day high resistance breakout | `breakout` | `lookback_days`(int)=20, `breakout_margin_pct`(float)=0.0 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `resistance_retest_signal` | Price retests resistance and closes below | `price_action` | `resistance_lookback`(int)=40, `tolerance_pct`(float)=1.0 | 기본값으로 시작 후 민감도(±20~30%) 테스트 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_FACTORS` |
| `return_kurtosis_filter` | Return kurtosis filter | `risk` | `lookback_days`(int)=60, `max_kurtosis`(float)=10.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_FACTORS` |
| `return_skewness_filter` | Return skewness filter | `risk` | `lookback_days`(int)=60, `min_skewness`(float)=-1.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_FACTORS` |
| `return_turnaround` | Previous N-day return <= threshold and recent N-day return >= threshold | `price` | `period_days`(int)=5, `prev_max_return_pct`(float)=-2.0, `min_return_pct`(float)=2.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_FACTORS` |
| `revenue_cagr_3y` | 3-year revenue CAGR | `fundamental` | `min_cagr_pct`(float)=5.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `revenue_growth_yoy` | Year-over-year revenue growth | `fundamental` | `min_growth_pct`(float)=5.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `revenue_stability_score` | Revenue stability based on coefficient of variation | `fundamental` | `lookback_years`(int)=5, `max_cv`(float)=0.25 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `roa_filter` | Return on assets | `fundamental` | `min_roa_pct`(float)=5.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `roce_filter` | Return on capital employed | `fundamental` | `min_roce_pct`(float)=10.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `roe` | Return on Equity filter | `Fundamental` | `min_roe`(float)=15.0, `max_roe`(float)=None | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `roic` | Return on Invested Capital filter | `Fundamental` | `min_roic`(float)=15.0, `max_roic`(float)=None | 범위형(min/max): 기본값 시작 후 후보 수 과다 시 범위 축소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `rolling_sharpe_filter` | Rolling Sharpe ratio filter | `risk` | `lookback_days`(int)=60, `min_sharpe`(float)=1.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_FACTORS` |
| `rolling_sortino_filter` | Rolling Sortino ratio filter | `risk` | `lookback_days`(int)=60, `min_sortino`(float)=1.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_FACTORS` |
| `rsi_overbought` | RSI above threshold | `rsi` | `threshold`(float)=70, `period`(int)=14 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 극단값(과매수/과매도)에 가까울수록 반전 신호 강도↑ | 강한 단방향 추세에서는 역추세 신호가 장기간 실패 가능 | `S_RSICORE` |
| `rsi_oversold` | RSI below threshold | `rsi` | `threshold`(float)=35, `period`(int)=14 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 극단값(과매수/과매도)에 가까울수록 반전 신호 강도↑ | 강한 단방향 추세에서는 역추세 신호가 장기간 실패 가능 | `S_RSICORE` |
| `rsi_range` | RSI within range | `rsi` | `lower`(float)=50, `upper`(float)=70, `period`(int)=14 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 극단값(과매수/과매도)에 가까울수록 반전 신호 강도↑ | 강한 단방향 추세에서는 역추세 신호가 장기간 실패 가능 | `S_RSICORE` |
| `semivariance_filter` | Downside semivariance filter | `risk` | `lookback_days`(int)=60, `max_semivariance`(float)=0.0004 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_FACTORS` |
| `shareholder_yield_filter` | Dividend + buyback - issuance yield | `fundamental` | `min_yield_pct`(float)=2.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `short_float_pct_filter` | Short float percentage threshold | `sentiment` | `max_short_float_pct`(float)=15.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 이벤트·캘린더 효과는 시기 의존성이 커 구간별 분리 해석 필요 | 거래비용·슬리피지 반영 시 유의미성 약화 가능 | `S_SHORT` |
| `short_interest_ratio_filter` | Days-to-cover threshold | `sentiment` | `max_ratio`(float)=5.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 이벤트·캘린더 효과는 시기 의존성이 커 구간별 분리 해석 필요 | 거래비용·슬리피지 반영 시 유의미성 약화 가능 | `S_SHORT` |
| `sma_slope` | SMA slope over lookback | `momentum` | `period`(int)=20, `lookback_days`(int)=5, `min_slope_pct`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `stochastic_cross_signal` | %K crossing above %D | `oscillator` | `k_period`(int)=14, `d_period`(int)=3, `lookback_days`(int)=5 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 극단값(과매수/과매도)에 가까울수록 반전 신호 강도↑ | 강한 단방향 추세에서는 역추세 신호가 장기간 실패 가능 | `S_STOCH` |
| `stochastic_divergence` | Price lower low + Stochastic higher low | `accumulation` | `k_period`(int)=14, `d_period`(int)=3, `lookback`(int)=20, `divergence_threshold`(float)=5.0 | 기본값으로 시작 후 민감도(±20~30%) 테스트 | 극단값(과매수/과매도)에 가까울수록 반전 신호 강도↑ | 강한 단방향 추세에서는 역추세 신호가 장기간 실패 가능 | `S_STOCH` |
| `stochastic_level` | Stochastic oscillator level | `accumulation` | `threshold`(float)=20.0, `condition`(str)=below, `k_period`(int)=14, `d_period`(int)=3 | 기본값으로 시작 후 민감도(±20~30%) 테스트 | 극단값(과매수/과매도)에 가까울수록 반전 신호 강도↑ | 강한 단방향 추세에서는 역추세 신호가 장기간 실패 가능 | `S_STOCH` |
| `stochrsi_signal` | StochRSI threshold signal | `oscillator` | `rsi_period`(int)=14, `stoch_period`(int)=14, `mode`(str)=oversold | 방향형: 전략 포지션과 일치 필요 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_FACTORS` |
| `support_retest_signal` | Price retests support and closes above | `price_action` | `support_lookback`(int)=40, `tolerance_pct`(float)=1.0 | 기본값으로 시작 후 민감도(±20~30%) 테스트 | 단독 사용보다 유동성+추세+리스크 조합 권장 | 인/아웃샘플 분리 검증 없이 실전 적용 금지 | `S_FACTORS` |
| `trix_cross` | TRIX crossing signal line | `momentum` | `period`(int)=15, `signal_period`(int)=9, `lookback_days`(int)=5, `direction`(str)=bullish | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `turn_of_month_effect` | Turn-of-month return effect | `time` | `window_days`(int)=3, `min_avg_return_pct`(float)=0.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 이벤트·캘린더 효과는 시기 의존성이 커 구간별 분리 해석 필요 | 거래비용·슬리피지 반영 시 유의미성 약화 가능 | `S_SEASONAL` |
| `turnover_ratio_min` | Minimum turnover ratio | `volume` | `min_turnover_ratio`(float)=0.01 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 밸류/품질 지표는 저평가·재무건전성 방향(조건별 min/max)에 따라 해석 | 공시 지연/일회성 회계 항목으로 왜곡 가능 | `S_VAL` |
| `ulcer_index_filter` | Ulcer index filter | `risk` | `lookback_days`(int)=60, `max_ulcer_index`(float)=10.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_FACTORS` |
| `ultimate_oscillator_signal` | Ultimate oscillator threshold | `oscillator` | `min_value`(float)=50.0 | 최소값형(min): 높일수록 엄격, 신호 수 감소 | 극단값(과매수/과매도)에 가까울수록 반전 신호 강도↑ | 강한 단방향 추세에서는 역추세 신호가 장기간 실패 가능 | `S_FACTORS` |
| `volatility_n_day` | Annualized N-day volatility filter | `risk` | `lookback_days`(int)=60, `max_annualized_vol_pct`(float)=25.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 변동성/낙폭/하방위험 값이 낮을수록 방어적 성향 강화 | 필터를 너무 조이면 기대수익 구간까지 제거될 수 있음 | `S_FACTORS` |
| `volume_above_avg` | Volume above moving average | `volume` | `multiplier`(float)=1.0, `period`(int)=20 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 거래량/자금흐름 지표는 가격 대비 선행/확인 신호로 사용 | 저유동성 구간에서 지표 안정성 저하 | `S_FACTORS` |
| `volume_below_avg` | Quiet volume zone | `accumulation` | `multiplier`(float)=1.0, `period`(int)=20 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 거래량/자금흐름 지표는 가격 대비 선행/확인 신호로 사용 | 저유동성 구간에서 지표 안정성 저하 | `S_FACTORS` |
| `volume_spike` | Sudden volume increase | `volume` | `multiplier`(float)=1.5, `period`(int)=20 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 거래량/자금흐름 지표는 가격 대비 선행/확인 신호로 사용 | 저유동성 구간에서 지표 안정성 저하 | `S_FACTORS` |
| `vpci_divergence` | Price flat + VPCI rising (quiet accumulation) | `accumulation` | `price_max_range_pct`(float)=5.0, `short_period`(int)=5, `long_period`(int)=20, `lookback`(int)=20 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 거래량/자금흐름 지표는 가격 대비 선행/확인 신호로 사용 | 저유동성 구간에서 지표 안정성 저하 | `S_FACTORS` |
| `vpci_trend` | Volume Price Confirmation Indicator trend | `accumulation` | `direction`(str)=up, `short_period`(int)=5, `long_period`(int)=20, `lookback`(int)=10 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_FACTORS` |
| `vwap_cross_signal` | Close crossing above VWAP | `volume` | `period`(int)=20, `lookback_days`(int)=3 | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_VWAP` |
| `vwap_distance_pct` | Distance between close and VWAP | `volume` | `period`(int)=20, `max_distance_pct`(float)=5.0 | 최대값형(max): 낮출수록 엄격, 리스크 노출 감소 | 상향 돌파/정배열/양(+) 기울기일수록 추세 지속 신호로 해석 | 횡보장에서는 휩쏘(가짜 돌파) 빈도 증가 | `S_VWAP` |
| `williams_r_reversal` | Williams %R reversal signal | `momentum` | `period`(int)=14, `oversold`(float)=-80, `overbought`(float)=-20, `direction`(str)=bullish | 기간형: 짧게=민감/노이즈↑, 길게=완만/안정↑ | 극단값(과매수/과매도)에 가까울수록 반전 신호 강도↑ | 강한 단방향 추세에서는 역추세 신호가 장기간 실패 가능 | `S_WILLR` |

## 실전 적용 순서(권장)
- 1) 유동성 필터 고정: `min_volume`, `avg_trading_value`, `turnover_ratio_min`
- 2) 전략 축 선택: 추세/역추세/이벤트 중 1~2개만 우선 적용
- 3) 리스크 제한: `volatility`, `drawdown`, `ulcer`, `beta` 계열로 tail risk 제어
- 4) fundamental/quality 조건은 마지막에 얇게 추가 (과필터링 방지)
- 5) 튜닝은 default 기준 ±20~30% 3점 비교 후 아웃샘플 검증
