# Condition Logic Inventory

- Generated at: 2026-03-12 14:43 UTC
- Registered metadata conditions: 164
- Class map entries (including aliases): 178

| key | category | is_pairs | params | class | module |
|---|---|---:|---:|---|---|
| `above_ma` | `movingAverage` | `false` | `2` | `AboveMACondition` | `screener.conditions.ma` |
| `accruals_ratio` | `quality` | `false` | `1` | `AccrualsRatioCondition` | `screener.conditions.quant_special_batch11` |
| `ad_line_trend` | `moneyflow` | `false` | `1` | `ADLineTrendCondition` | `screener.conditions.quant_oscillators` |
| `adx_trend_strength` | `momentum` | `false` | `3` | `ADXTrendStrengthCondition` | `screener.conditions.quant_trend` |
| `altman_zscore` | `fundamental` | `false` | `2` | `AltmanZScoreCondition` | `screener.conditions.fundamental` |
| `analyst_revision_1m` | `fundamental` | `false` | `1` | `AnalystRevision1MCondition` | `screener.conditions.quant_statistical` |
| `analyst_revision_3m` | `fundamental` | `false` | `1` | `AnalystRevision3MCondition` | `screener.conditions.quant_statistical` |
| `aroon_oscillator_signal` | `oscillator` | `false` | `2` | `AroonOscillatorSignalCondition` | `screener.conditions.quant_oscillators` |
| `aroon_trend_signal` | `momentum` | `false` | `3` | `AroonTrendSignalCondition` | `screener.conditions.momentum` |
| `asset_growth_rate` | `quality` | `false` | `1` | `AssetGrowthRateCondition` | `screener.conditions.quant_special_batch11` |
| `asset_turnover_ratio` | `fundamental` | `false` | `1` | `AssetTurnoverRatioCondition` | `screener.conditions.quant_fundamental_batch8` |
| `atr_expansion_breakout` | `risk` | `false` | `3` | `ATRExpansionBreakoutCondition` | `screener.conditions.quant_indicators` |
| `atr_percentile_filter` | `risk` | `false` | `3` | `ATRPercentileFilterCondition` | `screener.conditions.quant_indicators` |
| `avg_trading_value` | `volume` | `false` | `2` | `AvgTradingValueCondition` | `screener.conditions.volume` |
| `below_ma` | `movingAverage` | `false` | `2` | `BelowMACondition` | `screener.conditions.ma` |
| `beta_to_benchmark` | `risk` | `false` | `2` | `BetaToBenchmarkCondition` | `screener.conditions.quant_statistical` |
| `bollinger_percent_b` | `oscillator` | `false` | `4` | `BollingerPercentBCondition` | `screener.conditions.quant_oscillators` |
| `bollinger_squeeze_breakout` | `oscillator` | `false` | `3` | `BollingerSqueezeBreakoutCondition` | `screener.conditions.quant_oscillators` |
| `bollinger_width` | `accumulation` | `false` | `3` | `BollingerWidthCondition` | `screener.conditions.accumulation` |
| `book_to_market_ratio` | `fundamental` | `false` | `1` | `BookToMarketRatioCondition` | `screener.conditions.quant_fundamental_batch8` |
| `bottom_breakout` | `breakout` | `false` | `2` | `BottomBreakoutCondition` | `screener.conditions.breakout` |
| `breakout_with_volume` | `breakout` | `false` | `5` | `BreakoutWithVolumeCondition` | `screener.conditions.breakout` |
| `buyback_yield_filter` | `fundamental` | `false` | `1` | `BuybackYieldFilterCondition` | `screener.conditions.quant_shareholder_batch10` |
| `calmar_ratio_filter` | `risk` | `false` | `2` | `CalmarRatioFilterCondition` | `screener.conditions.risk` |
| `cash_conversion_ratio` | `fundamental` | `false` | `1` | `CashConversionRatioCondition` | `screener.conditions.quant_fundamental_batch9` |
| `cashflow_to_debt_ratio` | `fundamental` | `false` | `1` | `CashflowToDebtRatioCondition` | `screener.conditions.quant_fundamental_batch8` |
| `cci_overbought_oversold` | `momentum` | `false` | `3` | `CCIOverboughtOversoldCondition` | `screener.conditions.momentum` |
| `chaikin_money_flow_signal` | `moneyflow` | `false` | `2` | `ChaikinMoneyFlowSignalCondition` | `screener.conditions.quant_oscillators` |
| `chaikin_oscillator_signal` | `moneyflow` | `false` | `3` | `ChaikinOscillatorSignalCondition` | `screener.conditions.quant_oscillators` |
| `correlation_to_benchmark` | `risk` | `false` | `2` | `CorrelationToBenchmarkCondition` | `screener.conditions.quant_statistical` |
| `current_ratio` | `fundamental` | `false` | `2` | `CurrentRatioCondition` | `screener.conditions.fundamental` |
| `day_of_week_seasonality` | `time` | `false` | `2` | `DayOfWeekSeasonalityCondition` | `screener.conditions.time_price` |
| `death_cross_50_200` | `movingAverage` | `false` | `1` | `DeathCross50200Condition` | `screener.conditions.quant_trend` |
| `debt_service_coverage_ratio` | `fundamental` | `false` | `1` | `DebtServiceCoverageRatioCondition` | `screener.conditions.quant_fundamental_batch9` |
| `debt_to_equity` | `fundamental` | `false` | `2` | `DebtToEquityCondition` | `screener.conditions.fundamental` |
| `distance_from_200d_high` | `price` | `false` | `2` | `DistanceFrom200DHighCondition` | `screener.conditions.time_price` |
| `distance_from_52w_high` | `price` | `false` | `2` | `DistanceFrom52WHighCondition` | `screener.conditions.quant_trend` |
| `distance_from_52w_low` | `price` | `false` | `2` | `DistanceFrom52WLowCondition` | `screener.conditions.time_price` |
| `dividend_growth_5y` | `fundamental` | `false` | `1` | `DividendGrowth5YCondition` | `screener.conditions.quant_shareholder_batch10` |
| `dividend_yield` | `fundamental` | `false` | `2` | `DividendYieldCondition` | `screener.conditions.fundamental` |
| `dmi_directional_cross` | `momentum` | `false` | `2` | `DMIDirectionalCrossCondition` | `screener.conditions.quant_indicators` |
| `donchian_channel_breakout` | `breakout` | `false` | `1` | `DonchianChannelBreakoutCondition` | `screener.conditions.quant_trend` |
| `downside_volatility_filter` | `risk` | `false` | `2` | `DownsideVolatilityFilterCondition` | `screener.conditions.risk` |
| `drawdown_from_high` | `price` | `false` | `3` | `DrawdownFromHighCondition` | `screener.conditions.price` |
| `dso_trend_filter` | `fundamental` | `false` | `2` | `DsoTrendFilterCondition` | `screener.conditions.fundamental` |
| `earnings_stability_score` | `fundamental` | `false` | `2` | `EarningsStabilityScoreCondition` | `screener.conditions.quant_fundamental_batch9` |
| `earnings_surprise_filter` | `event` | `false` | `1` | `EarningsSurpriseFilterCondition` | `screener.conditions.quant_special_batch11` |
| `earnings_yield` | `fundamental` | `false` | `2` | `EarningsYieldCondition` | `screener.conditions.fundamental` |
| `ebit_ev` | `fundamental` | `false` | `2` | `EbitEvCondition` | `screener.conditions.fundamental` |
| `ema_cross` | `momentum` | `false` | `4` | `EMACrossCondition` | `screener.conditions.momentum` |
| `ema_slope` | `momentum` | `false` | `3` | `EMASlopeCondition` | `screener.conditions.momentum` |
| `eps_cagr_3y` | `fundamental` | `false` | `1` | `EPSCAGR3YCondition` | `screener.conditions.quant_fundamental_batch8` |
| `eps_growth_yoy` | `fundamental` | `false` | `1` | `EPSGrowthYoYCondition` | `screener.conditions.quant_fundamental_batch8` |
| `ev_to_ebitda_ratio` | `fundamental` | `false` | `1` | `EVToEbitdaRatioCondition` | `screener.conditions.quant_fundamental_batch8` |
| `ev_to_sales_ratio` | `fundamental` | `false` | `1` | `EVToSalesRatioCondition` | `screener.conditions.quant_fundamental_batch8` |
| `fcf_yield` | `fundamental` | `false` | `2` | `FcfYieldCondition` | `screener.conditions.fundamental` |
| `free_cash_flow_margin` | `fundamental` | `false` | `1` | `FreeCashFlowMarginCondition` | `screener.conditions.quant_shareholder_batch10` |
| `fresh_breakout` | `breakout` | `false` | `2` | `FreshBreakoutCondition` | `screener.conditions.breakout` |
| `gap_down_exhaustion` | `price` | `false` | `1` | `GapDownExhaustionCondition` | `screener.conditions.time_price` |
| `gap_up_breakaway` | `price` | `false` | `1` | `GapUpBreakawayCondition` | `screener.conditions.time_price` |
| `golden_cross_50_200` | `movingAverage` | `false` | `1` | `GoldenCross50200Condition` | `screener.conditions.quant_trend` |
| `gross_margin` | `fundamental` | `false` | `1` | `GrossMarginCondition` | `screener.conditions.quant_shareholder_batch10` |
| `gross_profitability` | `quality` | `false` | `1` | `GrossProfitabilityCondition` | `screener.conditions.quant_special_batch11` |
| `ichimoku_cloud_breakout` | `momentum` | `false` | `3` | `IchimokuCloudBreakoutCondition` | `screener.conditions.quant_indicators` |
| `ichimoku_tenkan_kijun_cross` | `momentum` | `false` | `3` | `IchimokuTenkanKijunCrossCondition` | `screener.conditions.quant_indicators` |
| `insider_net_buying` | `fundamental` | `false` | `1` | `InsiderNetBuyingCondition` | `screener.conditions.quant_shareholder_batch10` |
| `interest_coverage_ratio` | `fundamental` | `false` | `1` | `InterestCoverageRatioCondition` | `screener.conditions.quant_fundamental_batch9` |
| `intraday_return_filter` | `risk` | `false` | `1` | `IntradayReturnFilterCondition` | `screener.conditions.risk` |
| `inventory_turnover_ratio` | `fundamental` | `false` | `1` | `InventoryTurnoverRatioCondition` | `screener.conditions.quant_fundamental_batch8` |
| `keltner_channel_breakout` | `breakout` | `false` | `3` | `KeltnerChannelBreakoutCondition` | `screener.conditions.quant_trend` |
| `linear_regression_angle_filter` | `momentum` | `false` | `2` | `LinearRegressionAngleFilterCondition` | `screener.conditions.quant_statistical` |
| `linear_regression_r2_filter` | `momentum` | `false` | `2` | `LinearRegressionR2FilterCondition` | `screener.conditions.quant_statistical` |
| `linear_regression_slope_filter` | `momentum` | `false` | `2` | `LinearRegressionSlopeFilterCondition` | `screener.conditions.quant_statistical` |
| `ma_cross_down` | `movingAverage` | `false` | `3` | `MACrossDownCondition` | `screener.conditions.ma` |
| `ma_cross_up` | `movingAverage` | `false` | `3` | `MACrossUpCondition` | `screener.conditions.ma` |
| `ma_ribbon_alignment` | `movingAverage` | `false` | `3` | `MARibbonAlignmentCondition` | `screener.conditions.quant_trend` |
| `ma_touch` | `movingAverage` | `false` | `2` | `MATouchCondition` | `screener.conditions.ma` |
| `macd_histogram_slope` | `momentum` | `false` | `5` | `MACDHistogramSlopeCondition` | `screener.conditions.momentum` |
| `macd_signal_cross` | `momentum` | `false` | `5` | `MACDSignalCrossCondition` | `screener.conditions.momentum` |
| `max_drawdown_window_filter` | `risk` | `false` | `2` | `MaxDrawdownWindowFilterCondition` | `screener.conditions.risk` |
| `max_price` | `price` | `false` | `1` | `MaxPriceCondition` | `screener.conditions.price` |
| `min_price` | `price` | `false` | `1` | `MinPriceCondition` | `screener.conditions.price` |
| `min_volume` | `volume` | `false` | `1` | `MinVolumeCondition` | `screener.conditions.volume` |
| `momentum_12_1` | `momentum` | `false` | `3` | `Momentum121Condition` | `screener.conditions.quant_trend` |
| `money_flow_index_signal` | `momentum` | `false` | `4` | `MoneyFlowIndexSignalCondition` | `screener.conditions.momentum` |
| `month_of_year_seasonality` | `time` | `false` | `2` | `MonthOfYearSeasonalityCondition` | `screener.conditions.time_price` |
| `natr_filter` | `risk` | `false` | `2` | `NATRFilterCondition` | `screener.conditions.quant_indicators` |
| `net_debt_to_ebitda` | `fundamental` | `false` | `1` | `NetDebtToEbitdaCondition` | `screener.conditions.quant_fundamental_batch9` |
| `net_margin` | `fundamental` | `false` | `1` | `NetMarginCondition` | `screener.conditions.quant_shareholder_batch10` |
| `net_share_issuance_filter` | `fundamental` | `false` | `1` | `NetShareIssuanceFilterCondition` | `screener.conditions.quant_shareholder_batch10` |
| `obv_divergence` | `accumulation` | `false` | `3` | `OBVDivergenceCondition` | `screener.conditions.accumulation` |
| `obv_trend` | `accumulation` | `false` | `2` | `OBVTrendCondition` | `screener.conditions.accumulation` |
| `opening_range_breakout` | `price` | `false` | `1` | `OpeningRangeBreakoutCondition` | `screener.conditions.time_price` |
| `operating_margin` | `fundamental` | `false` | `1` | `OperatingMarginCondition` | `screener.conditions.quant_shareholder_batch10` |
| `overnight_return_filter` | `time` | `false` | `1` | `OvernightReturnFilterCondition` | `screener.conditions.time_price` |
| `pair_cointegration` | `pairs` | `true` | `3` | `PairCointegrationCondition` | `screener.conditions.pairs_trading` |
| `pair_correlation` | `pairs` | `true` | `3` | `PairCorrelationCondition` | `screener.conditions.pairs_trading` |
| `pair_spread_zscore` | `pairs` | `true` | `4` | `PairSpreadZScoreCondition` | `screener.conditions.pairs_trading` |
| `parabolic_sar_flip` | `momentum` | `false` | `3` | `ParabolicSARFlipCondition` | `screener.conditions.quant_statistical` |
| `payout_ratio_filter` | `fundamental` | `false` | `1` | `PayoutRatioFilterCondition` | `screener.conditions.quant_shareholder_batch10` |
| `pb_ratio` | `fundamental` | `false` | `3` | `PBRatioCondition` | `screener.conditions.fundamental` |
| `pcf_ratio` | `fundamental` | `false` | `2` | `PCFRatioCondition` | `screener.conditions.fundamental` |
| `pe_ratio` | `fundamental` | `false` | `2` | `PERatioCondition` | `screener.conditions.fundamental` |
| `peg_ratio` | `fundamental` | `false` | `2` | `PegRatioCondition` | `screener.conditions.fundamental` |
| `piotroski_fscore` | `fundamental` | `false` | `2` | `PiotroskiFScoreCondition` | `screener.conditions.fundamental` |
| `pivot_point_breakout` | `price` | `false` | `1` | `PivotPointBreakoutCondition` | `screener.conditions.time_price` |
| `post_earnings_drift` | `event` | `false` | `1` | `PostEarningsDriftCondition` | `screener.conditions.quant_special_batch11` |
| `ppo_signal_cross` | `oscillator` | `false` | `4` | `PPOSignalCrossCondition` | `screener.conditions.quant_oscillators` |
| `pre_earnings_drift` | `event` | `false` | `1` | `PreEarningsDriftCondition` | `screener.conditions.quant_special_batch11` |
| `price_change` | `price` | `false` | `3` | `PriceChangeCondition` | `screener.conditions.price` |
| `price_flat` | `accumulation` | `false` | `2` | `PriceFlatCondition` | `screener.conditions.accumulation` |
| `price_lag_compare` | `price` | `false` | `4` | `PriceLagCompareCondition` | `screener.conditions.basic_catalog` |
| `price_range` | `price` | `false` | `2` | `PriceRangeCondition` | `screener.conditions.price` |
| `price_to_tangible_book` | `fundamental` | `false` | `1` | `PriceToTangibleBookCondition` | `screener.conditions.quant_fundamental_batch8` |
| `ps_ratio` | `fundamental` | `false` | `2` | `PSRatioCondition` | `screener.conditions.fundamental` |
| `quality_score` | `quality` | `false` | `1` | `QualityScoreCondition` | `screener.conditions.quant_special_batch11` |
| `receivables_turnover_ratio` | `fundamental` | `false` | `1` | `ReceivablesTurnoverRatioCondition` | `screener.conditions.quant_fundamental_batch8` |
| `relative_strength_vs_benchmark` | `momentum` | `false` | `2` | `RelativeStrengthVsBenchmarkCondition` | `screener.conditions.quant_trend` |
| `relative_volume_percentile` | `volume` | `false` | `2` | `RelativeVolumePercentileCondition` | `screener.conditions.quant_indicators` |
| `resistance_breakout` | `breakout` | `false` | `2` | `ResistanceBreakoutCondition` | `screener.conditions.breakout` |
| `resistance_retest_signal` | `price_action` | `false` | `2` | `ResistanceRetestSignalCondition` | `screener.conditions.quant_statistical` |
| `return_kurtosis_filter` | `risk` | `false` | `2` | `ReturnKurtosisFilterCondition` | `screener.conditions.risk` |
| `return_pct_range` | `price` | `false` | `3` | `ReturnRangeCondition` | `screener.conditions.basic_catalog` |
| `return_skewness_filter` | `risk` | `false` | `2` | `ReturnSkewnessFilterCondition` | `screener.conditions.risk` |
| `return_turnaround` | `price` | `false` | `3` | `ReturnTurnaroundCondition` | `screener.conditions.price` |
| `revenue_cagr_3y` | `fundamental` | `false` | `1` | `RevenueCAGR3YCondition` | `screener.conditions.quant_fundamental_batch9` |
| `revenue_growth_yoy` | `fundamental` | `false` | `1` | `RevenueGrowthYoYCondition` | `screener.conditions.quant_fundamental_batch9` |
| `revenue_stability_score` | `fundamental` | `false` | `2` | `RevenueStabilityScoreCondition` | `screener.conditions.quant_fundamental_batch9` |
| `roa_filter` | `fundamental` | `false` | `1` | `ROAFilterCondition` | `screener.conditions.quant_fundamental_batch9` |
| `roce_filter` | `fundamental` | `false` | `1` | `ROCEFilterCondition` | `screener.conditions.quant_fundamental_batch9` |
| `roe` | `fundamental` | `false` | `2` | `RoeCondition` | `screener.conditions.fundamental` |
| `roic` | `fundamental` | `false` | `2` | `RoicCondition` | `screener.conditions.fundamental` |
| `rolling_sharpe_filter` | `risk` | `false` | `2` | `RollingSharpeFilterCondition` | `screener.conditions.risk` |
| `rolling_sortino_filter` | `risk` | `false` | `2` | `RollingSortinoFilterCondition` | `screener.conditions.risk` |
| `rsi_overbought` | `rsi` | `false` | `2` | `RSIOverboughtCondition` | `screener.conditions.rsi` |
| `rsi_oversold` | `rsi` | `false` | `2` | `RSIOversoldCondition` | `screener.conditions.rsi` |
| `rsi_range` | `rsi` | `false` | `3` | `RSIRangeCondition` | `screener.conditions.rsi` |
| `semivariance_filter` | `risk` | `false` | `2` | `SemivarianceFilterCondition` | `screener.conditions.risk` |
| `shareholder_yield_filter` | `fundamental` | `false` | `1` | `ShareholderYieldFilterCondition` | `screener.conditions.quant_shareholder_batch10` |
| `short_float_pct_filter` | `sentiment` | `false` | `1` | `ShortFloatPctFilterCondition` | `screener.conditions.quant_special_batch11` |
| `short_interest_ratio_filter` | `sentiment` | `false` | `1` | `ShortInterestRatioFilterCondition` | `screener.conditions.quant_special_batch11` |
| `sma_slope` | `momentum` | `false` | `3` | `SMASlopeCondition` | `screener.conditions.momentum` |
| `stochastic_cross_signal` | `oscillator` | `false` | `3` | `StochasticCrossSignalCondition` | `screener.conditions.quant_oscillators` |
| `stochastic_divergence` | `accumulation` | `false` | `4` | `StochasticDivergenceCondition` | `screener.conditions.accumulation` |
| `stochastic_level` | `accumulation` | `false` | `4` | `StochasticLevelCondition` | `screener.conditions.accumulation` |
| `stochrsi_signal` | `oscillator` | `false` | `3` | `StochRSISignalCondition` | `screener.conditions.quant_oscillators` |
| `supertrend_signal` | `trend` | `false` | `4` | `SupertrendSignalCondition` | `screener.conditions.quant_trend` |
| `support_retest_signal` | `price_action` | `false` | `2` | `SupportRetestSignalCondition` | `screener.conditions.quant_statistical` |
| `trix_cross` | `momentum` | `false` | `4` | `TRIXCrossCondition` | `screener.conditions.momentum` |
| `turn_of_month_effect` | `time` | `false` | `2` | `TurnOfMonthEffectCondition` | `screener.conditions.time_price` |
| `turnover_ratio_min` | `volume` | `false` | `1` | `TurnoverRatioMinCondition` | `screener.conditions.quant_indicators` |
| `ulcer_index_filter` | `risk` | `false` | `2` | `UlcerIndexFilterCondition` | `screener.conditions.risk` |
| `ultimate_oscillator_signal` | `oscillator` | `false` | `1` | `UltimateOscillatorSignalCondition` | `screener.conditions.quant_oscillators` |
| `volatility_n_day` | `risk` | `false` | `2` | `VolatilityNDayCondition` | `screener.conditions.quant_trend` |
| `volume_above_avg` | `volume` | `false` | `2` | `VolumeAboveAvgCondition` | `screener.conditions.volume` |
| `volume_below_avg` | `accumulation` | `false` | `2` | `VolumeBelowAvgCondition` | `screener.conditions.accumulation` |
| `volume_lag_compare` | `volume` | `false` | `3` | `VolumeLagCompareCondition` | `screener.conditions.basic_catalog` |
| `volume_ma_ratio` | `volume` | `false` | `4` | `VolumeMARatioCondition` | `screener.conditions.basic_catalog` |
| `volume_spike` | `volume` | `false` | `2` | `VolumeSpikeCondition` | `screener.conditions.volume` |
| `vpci_divergence` | `accumulation` | `false` | `4` | `VPCIDivergenceCondition` | `screener.conditions.accumulation` |
| `vpci_trend` | `accumulation` | `false` | `4` | `VPCITrendCondition` | `screener.conditions.accumulation` |
| `vwap_cross_signal` | `volume` | `false` | `2` | `VWAPCrossSignalCondition` | `screener.conditions.quant_indicators` |
| `vwap_distance_pct` | `volume` | `false` | `2` | `VWAPDistancePctCondition` | `screener.conditions.quant_indicators` |
| `williams_r_reversal` | `momentum` | `false` | `4` | `WilliamsRReversalCondition` | `screener.conditions.momentum` |

## Alias Keys (class_map only)

- `return_pct_10d_minmax` -> `partial` (functools)
- `return_pct_1d_minmax` -> `partial` (functools)
- `return_pct_20d_minmax` -> `partial` (functools)
- `return_pct_2d_minmax` -> `partial` (functools)
- `return_pct_3d_minmax` -> `partial` (functools)
- `return_pct_5d_minmax` -> `partial` (functools)
- `volume_ma_ratio_10_20` -> `partial` (functools)
- `volume_ma_ratio_10_60` -> `partial` (functools)
- `volume_ma_ratio_2_20` -> `partial` (functools)
- `volume_ma_ratio_2_60` -> `partial` (functools)
- `volume_ma_ratio_3_20` -> `partial` (functools)
- `volume_ma_ratio_3_60` -> `partial` (functools)
- `volume_ma_ratio_5_20` -> `partial` (functools)
- `volume_ma_ratio_5_60` -> `partial` (functools)