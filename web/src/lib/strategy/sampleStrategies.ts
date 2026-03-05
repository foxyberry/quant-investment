import type { StrategyGraph } from './graphSerializer';

export type PresetCategory =
  | 'trend_following'
  | 'momentum'
  | 'mean_reversion'
  | 'breakout'
  | 'volume_flow'
  | 'volatility'
  | 'ichimoku'
  | 'fundamental';

export interface SampleStrategyPreset {
  key: string;
  category: PresetCategory;
  name: string;
  description: string;
  reference?: string;
  graph: StrategyGraph;
}

export const PRESET_CATEGORY_ORDER: PresetCategory[] = [
  'trend_following',
  'momentum',
  'mean_reversion',
  'breakout',
  'volume_flow',
  'volatility',
  'ichimoku',
  'fundamental',
];

type ConditionSpec = {
  condition_type: string;
  params: Record<string, unknown>;
};

function buildLinearGraph(universe: string, conditions: ConditionSpec[]): StrategyGraph {
  const nodes: StrategyGraph['nodes'] = [
    {
      id: 'sample_universe',
      data: { node_type: 'universe', universe },
      position: { x: 60, y: 190 },
    },
  ];

  const edges: StrategyGraph['edges'] = [];
  let prevId = 'sample_universe';

  for (let i = 0; i < conditions.length; i += 1) {
    const condId = `sample_cond_${i + 1}`;
    nodes.push({
      id: condId,
      data: {
        node_type: 'condition',
        condition_type: conditions[i].condition_type,
        params: conditions[i].params,
      },
      position: { x: 300 + i * 260, y: 160 },
    });
    edges.push({
      id: `sample_edge_${i + 1}`,
      source: prevId,
      target: condId,
    });
    prevId = condId;
  }

  nodes.push({
    id: 'sample_output',
    data: { node_type: 'output' },
    position: { x: 300 + conditions.length * 260, y: 190 },
  });
  edges.push({
    id: `sample_edge_${conditions.length + 1}`,
    source: prevId,
    target: 'sample_output',
  });

  return { nodes, edges };
}

export const SAMPLE_STRATEGY_PRESETS: SampleStrategyPreset[] = [
  {
    key: 'trend_following_52w_breakout',
    category: 'breakout',
    name: '52주 신고가 돌파 (추세추종)',
    description: '52주 고점 근접 + 거래량 급증 조합으로 돌파 추세를 추종합니다.',
    reference: 'Trend following / 52-week breakout',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'distance_from_52w_high', params: { lookback_days: 252, max_distance_pct: 3 } },
      { condition_type: 'volume_above_avg', params: { multiplier: 1.5, period: 20 } },
    ]),
  },
  {
    key: 'dual_momentum_relative_strength',
    category: 'momentum',
    name: '듀얼 모멘텀 (상대강도)',
    description: '시장 대비 상대 강도 + 12-1 모멘텀으로 강한 종목만 선별합니다.',
    reference: 'Dual momentum',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'relative_strength_vs_benchmark', params: { lookback_days: 120, min_excess_return_pct: 3 } },
      { condition_type: 'momentum_12_1', params: { lookback_months: 12, skip_recent_months: 1, min_return_pct: 10 } },
    ]),
  },
  {
    key: 'rsi_mean_reversion',
    category: 'mean_reversion',
    name: 'RSI 과매도 평균회귀',
    description: '과매도 구간에서 거래량 확인을 추가해 반등 후보를 찾습니다.',
    reference: 'RSI mean reversion',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'rsi_oversold', params: { threshold: 35, period: 14 } },
      { condition_type: 'volume_above_avg', params: { multiplier: 1.2, period: 20 } },
    ]),
  },
  {
    key: 'golden_cross_trend',
    category: 'trend_following',
    name: '골든크로스 추세 전략',
    description: '50/200 이평선 골든크로스와 거래대금 필터를 결합합니다.',
    reference: 'Golden cross',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'golden_cross_50_200', params: { lookback_days: 10 } },
      { condition_type: 'avg_trading_value', params: { lookback_days: 20, min_value: 10000000 } },
    ]),
  },
  {
    key: 'bollinger_squeeze_breakout',
    category: 'volatility',
    name: '볼린저 스퀴즈 돌파',
    description: '변동성 압축 후 돌파 구간을 포착합니다.',
    reference: 'Bollinger squeeze breakout',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'bollinger_squeeze_breakout', params: { period: 20, std_mult: 2.0, max_width_pct: 8 } },
      { condition_type: 'breakout_with_volume', params: { lookback_days: 20, breakout_pct: 1.5, volume_ratio: 1.5, volume_avg_days: 20, fresh_only: true } },
    ]),
  },
  {
    key: 'turtle_donchian_breakout',
    category: 'breakout',
    name: '터틀 돈치안 돌파',
    description: '돈치안 채널 돌파에 ATR 기반 변동성 확인을 추가합니다.',
    reference: 'Turtle trading',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'donchian_channel_breakout', params: { lookback_days: 20 } },
      { condition_type: 'atr_expansion_breakout', params: { atr_period: 14, atr_multiplier: 1.2, breakout_lookback: 20 } },
    ]),
  },
  {
    key: 'value_quality_combo',
    category: 'fundamental',
    name: '밸류 + 퀄리티',
    description: '저평가(PE/PB)와 재무건전성(ROE/피오트로스키)을 결합합니다.',
    reference: 'Value + quality factors',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'pe_ratio', params: { min_pe: 0, max_pe: 15 } },
      { condition_type: 'pb_ratio', params: { min_pb: 0, max_pb: 1.5, exclude_negative_bv: true } },
      { condition_type: 'roe', params: { min_roe: 10, max_roe: 100 } },
      { condition_type: 'piotroski_fscore', params: { min_score: 6, max_score: 9 } },
    ]),
  },
  {
    key: 'low_volatility_defensive',
    category: 'fundamental',
    name: '로우볼(저변동성) 방어형',
    description: '낮은 변동성과 낮은 베타 조합으로 방어형 종목을 찾습니다.',
    reference: 'Low volatility anomaly',
    graph: buildLinearGraph('SP500', [
      { condition_type: 'volatility_n_day', params: { lookback_days: 60, max_annualized_vol_pct: 25 } },
      { condition_type: 'beta_to_benchmark', params: { lookback_days: 120, max_beta: 0.9 } },
    ]),
  },
  {
    key: 'post_earnings_drift',
    category: 'fundamental',
    name: '실적 발표 후 드리프트',
    description: '실적 발표 후 모멘텀 지속 구간을 포착합니다.',
    reference: 'Post-earnings announcement drift',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'earnings_surprise_filter', params: { min_surprise_pct: 5 } },
      { condition_type: 'post_earnings_drift', params: { min_return_pct: 2.0 } },
    ]),
  },
  {
    key: 'short_term_breakout_liquidity',
    category: 'breakout',
    name: '단기 돌파 + 유동성 필터',
    description: '신규 고점 돌파와 충분한 거래량/거래대금을 동시에 확인합니다.',
    reference: 'Breakout + liquidity filter',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'fresh_breakout', params: { lookback_days: 55, breakout_pct: 2 } },
      { condition_type: 'volume_spike', params: { multiplier: 2.0, period: 20 } },
      { condition_type: 'avg_trading_value', params: { lookback_days: 20, min_value: 5000000000 } },
    ]),
  },
  {
    key: 'ema_cross_momentum',
    category: 'momentum',
    name: 'EMA 크로스 모멘텀',
    description: 'EMA 골든크로스와 상대거래량으로 추세 전환 초기를 포착합니다.',
    reference: 'EMA crossover momentum',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'ema_cross', params: { fast_period: 12, slow_period: 26, lookback_days: 5, direction: 'bullish' } },
      { condition_type: 'relative_volume_percentile', params: { lookback_days: 60, min_percentile: 70 } },
    ]),
  },
  {
    key: 'macd_cross_trend',
    category: 'momentum',
    name: 'MACD 시그널 크로스',
    description: 'MACD 상향 교차 후 거래량이 동반되는 종목을 선별합니다.',
    reference: 'MACD signal crossover',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'macd_signal_cross', params: { fast_period: 12, slow_period: 26, signal_period: 9, lookback_days: 5, direction: 'bullish' } },
      { condition_type: 'volume_above_avg', params: { multiplier: 1.3, period: 20 } },
    ]),
  },
  {
    key: 'stochastic_oversold_rebound',
    category: 'mean_reversion',
    name: '스토캐스틱 과매도 반등',
    description: '스토캐스틱 과매도 구간과 단기 가격 반전을 함께 확인합니다.',
    reference: 'Stochastic oversold rebound',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'stochastic_level', params: { threshold: 20, condition: 'below', k_period: 14, d_period: 3 } },
      { condition_type: 'price_change', params: { min_change_pct: 0.5, max_change_pct: 7.0, days: 1 } },
    ]),
  },
  {
    key: 'williams_reversal_setup',
    category: 'mean_reversion',
    name: '윌리엄스 %R 리버설',
    description: '과매도 리버설 신호와 낮은 변동성 환경을 결합합니다.',
    reference: 'Williams %R reversal',
    graph: buildLinearGraph('SP500', [
      { condition_type: 'williams_r_reversal', params: { period: 14, oversold: -80, overbought: -20, direction: 'bullish' } },
      { condition_type: 'natr_filter', params: { period: 14, max_natr_pct: 6 } },
    ]),
  },
  {
    key: 'vwap_pullback_reentry',
    category: 'volume_flow',
    name: 'VWAP 눌림 재진입',
    description: 'VWAP 근접 눌림 구간에서 재상승 가능성을 노립니다.',
    reference: 'VWAP pullback',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'vwap_distance_pct', params: { period: 20, max_distance_pct: 1.5 } },
      { condition_type: 'vwap_cross_signal', params: { period: 20, lookback_days: 3 } },
    ]),
  },
  {
    key: 'atr_volatility_compression_break',
    category: 'volatility',
    name: 'ATR 변동성 수축 후 확장',
    description: '낮은 ATR 백분위 이후 확장 돌파를 탐색합니다.',
    reference: 'Volatility compression breakout',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'atr_percentile_filter', params: { atr_period: 14, lookback_days: 120, max_percentile: 35 } },
      { condition_type: 'atr_expansion_breakout', params: { atr_period: 14, atr_multiplier: 1.25, breakout_lookback: 20 } },
    ]),
  },
  {
    key: 'bollinger_midband_reclaim',
    category: 'mean_reversion',
    name: '볼린저 중단 회복',
    description: '볼린저 밴드 중심선 회복과 가격 탄력을 함께 확인합니다.',
    reference: 'Bollinger mid-band reclaim',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'bollinger_percent_b', params: { period: 20, std_mult: 2.0, min_percent_b: 0.45, max_percent_b: 0.85 } },
      { condition_type: 'price_change', params: { min_change_pct: 1.0, max_change_pct: 8.0, days: 3 } },
    ]),
  },
  {
    key: 'keltner_channel_expansion',
    category: 'volatility',
    name: '켈트너 채널 돌파',
    description: '켈트너 채널 상단 돌파와 상대거래량을 결합한 추세 전략입니다.',
    reference: 'Keltner channel breakout',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'keltner_channel_breakout', params: { ema_period: 20, atr_period: 10, atr_multiplier: 1.5 } },
      { condition_type: 'relative_volume_percentile', params: { lookback_days: 60, min_percentile: 65 } },
    ]),
  },
  {
    key: 'ichimoku_cloud_breakout_trend',
    category: 'ichimoku',
    name: '일목균형표 구름 돌파',
    description: '구름대 돌파 종목 중 추세 강도가 유지되는 종목을 찾습니다.',
    reference: 'Ichimoku cloud breakout',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'ichimoku_cloud_breakout', params: { conversion_period: 9, base_period: 26, span_b_period: 52 } },
      { condition_type: 'ema_slope', params: { period: 20, lookback_days: 10, min_slope_pct: 0.2 } },
    ]),
  },
  {
    key: 'tenkan_kijun_cross_continuation',
    category: 'ichimoku',
    name: '전환선-기준선 크로스',
    description: '전환선 상향교차 후 가격이 이평선 위에 있는 종목을 선별합니다.',
    reference: 'Ichimoku tenkan-kijun cross',
    graph: buildLinearGraph('SP500', [
      { condition_type: 'ichimoku_tenkan_kijun_cross', params: { conversion_period: 9, base_period: 26, lookback_days: 5 } },
      { condition_type: 'above_ma', params: { period: 50, min_distance_pct: 0 } },
    ]),
  },
  {
    key: 'ma_slope_trend_follow',
    category: 'trend_following',
    name: '이평선 기울기 추세',
    description: '중장기 이평선 우상향과 거래대금 조건으로 추세 종목을 추립니다.',
    reference: 'Moving average slope trend following',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'sma_slope', params: { period: 60, lookback_days: 20, min_slope_pct: 0.1 } },
      { condition_type: 'avg_trading_value', params: { lookback_days: 20, min_value: 2000000000 } },
    ]),
  },
  {
    key: 'ma_cross_upswing',
    category: 'trend_following',
    name: '단기/중기 이평 상향교차',
    description: '단기 이평이 중기 이평을 상향 돌파한 초기 구간을 노립니다.',
    reference: 'MA crossover upswing',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'ma_cross_up', params: { short_period: 20, long_period: 60, lookback_days: 5 } },
      { condition_type: 'volume_spike', params: { multiplier: 1.4, period: 20 } },
    ]),
  },
  {
    key: 'obv_accumulation_trend',
    category: 'volume_flow',
    name: 'OBV 누적 매집 추세',
    description: 'OBV 상승 추세와 가격 지지 확인으로 매집 구간을 탐지합니다.',
    reference: 'OBV accumulation',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'obv_trend', params: { direction: 'up', lookback: 20 } },
      { condition_type: 'support_retest_signal', params: { support_lookback: 60, tolerance_pct: 2.0 } },
    ]),
  },
  {
    key: 'resistance_break_then_retest',
    category: 'breakout',
    name: '저항 돌파 후 리테스트',
    description: '저항 돌파 이후 리테스트 성공 패턴을 필터링합니다.',
    reference: 'Breakout retest setup',
    graph: buildLinearGraph('SP500', [
      { condition_type: 'resistance_breakout', params: { lookback_days: 55, breakout_margin_pct: 1.0 } },
      { condition_type: 'resistance_retest_signal', params: { resistance_lookback: 55, tolerance_pct: 2.0 } },
    ]),
  },
  {
    key: 'opening_range_breakout',
    category: 'breakout',
    name: '시가 범위 돌파',
    description: '시가 범위 상단 돌파 종목 중 거래량이 동반된 케이스를 선별합니다.',
    reference: 'Opening range breakout',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'opening_range_breakout', params: { direction: 'up' } },
      { condition_type: 'min_volume', params: { min_volume: 300000 } },
    ]),
  },
  {
    key: 'pivot_breakout_followthrough',
    category: 'breakout',
    name: '피벗 포인트 돌파',
    description: '피벗 상향 돌파 후 단기 추세 지속 가능성을 확인합니다.',
    reference: 'Pivot point breakout',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'pivot_point_breakout', params: { direction: 'up' } },
      { condition_type: 'price_change', params: { min_change_pct: 0.5, max_change_pct: 9.0, days: 2 } },
    ]),
  },
  {
    key: 'parabolic_sar_flip',
    category: 'volatility',
    name: '파라볼릭 SAR 전환',
    description: 'SAR 상승 전환과 과도한 변동성 배제를 함께 적용합니다.',
    reference: 'Parabolic SAR reversal',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'parabolic_sar_flip', params: { lookback_days: 5, af_step: 0.02, af_max: 0.2 } },
      { condition_type: 'downside_volatility_filter', params: { lookback_days: 60, max_downside_vol_pct: 30 } },
    ]),
  },
  {
    key: 'trix_signal_bullish',
    category: 'momentum',
    name: 'TRIX 상승 신호',
    description: 'TRIX 상향 교차 이후 추세 지속 종목을 선별합니다.',
    reference: 'TRIX bullish crossover',
    graph: buildLinearGraph('SP500', [
      { condition_type: 'trix_cross', params: { period: 15, signal_period: 9, lookback_days: 5, direction: 'bullish' } },
      { condition_type: 'above_ma', params: { period: 100, min_distance_pct: 0 } },
    ]),
  },
  {
    key: 'ppo_momentum_continuation',
    category: 'momentum',
    name: 'PPO 모멘텀 지속',
    description: 'PPO 시그널 상향 교차와 상대강도 필터를 결합합니다.',
    reference: 'PPO momentum continuation',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'ppo_signal_cross', params: { fast_period: 12, slow_period: 26, signal_period: 9, lookback_days: 5 } },
      { condition_type: 'relative_strength_vs_benchmark', params: { lookback_days: 90, min_excess_return_pct: 2 } },
    ]),
  },
  {
    key: 'stochrsi_reentry',
    category: 'mean_reversion',
    name: 'StochRSI 재진입',
    description: 'StochRSI 과매도권 반등 구간을 빠르게 포착합니다.',
    reference: 'StochRSI reentry',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'stochrsi_signal', params: { rsi_period: 14, stoch_period: 14, mode: 'oversold' } },
      { condition_type: 'volume_above_avg', params: { multiplier: 1.15, period: 20 } },
    ]),
  },
  {
    key: 'chaikin_money_flow_accumulation',
    category: 'volume_flow',
    name: '차이킨 자금흐름 매집',
    description: '양(+)의 자금 유입과 가격 추세를 함께 확인합니다.',
    reference: 'Chaikin money flow',
    graph: buildLinearGraph('SP500', [
      { condition_type: 'chaikin_money_flow_signal', params: { period: 20, min_cmf: 0.05 } },
      { condition_type: 'ema_slope', params: { period: 30, lookback_days: 15, min_slope_pct: 0.1 } },
    ]),
  },
  {
    key: 'chaikin_oscillator_break',
    category: 'volume_flow',
    name: '차이킨 오실레이터 돌파',
    description: '차이킨 오실레이터 양전환과 거래량 급증을 결합합니다.',
    reference: 'Chaikin oscillator breakout',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'chaikin_oscillator_signal', params: { fast_period: 3, slow_period: 10, min_value: 0 } },
      { condition_type: 'volume_spike', params: { multiplier: 1.8, period: 20 } },
    ]),
  },
  {
    key: 'adline_breadth_confirmation',
    category: 'volume_flow',
    name: 'AD라인 확산 확인',
    description: '시장 확산 강도(AD라인)와 종목 추세를 함께 반영합니다.',
    reference: 'A/D line breadth confirmation',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'ad_line_trend', params: { lookback_days: 20 } },
      { condition_type: 'momentum_12_1', params: { lookback_months: 12, skip_recent_months: 1, min_return_pct: 8 } },
    ]),
  },
  {
    key: 'quality_growth_compounder',
    category: 'fundamental',
    name: '퀄리티 성장주',
    description: '높은 ROIC와 이익 성장률이 동반되는 종목을 찾습니다.',
    reference: 'Quality growth compounding',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'roic', params: { min_roic: 10, max_roic: 100 } },
      { condition_type: 'eps_growth_yoy', params: { min_growth_pct: 10 } },
      { condition_type: 'revenue_growth_yoy', params: { min_growth_pct: 8 } },
    ]),
  },
  {
    key: 'free_cashflow_quality',
    category: 'fundamental',
    name: '현금흐름 퀄리티',
    description: 'FCF 수익률과 현금흐름 기반 안정성을 중시하는 전략입니다.',
    reference: 'FCF quality factor',
    graph: buildLinearGraph('SP500', [
      { condition_type: 'fcf_yield', params: { min_fcf_yield: 3, max_fcf_yield: 25 } },
      { condition_type: 'cashflow_to_debt_ratio', params: { min_ratio: 0.3 } },
      { condition_type: 'interest_coverage_ratio', params: { min_ratio: 4.0 } },
    ]),
  },
  {
    key: 'shareholder_yield_value',
    category: 'fundamental',
    name: '주주환원 밸류',
    description: '배당/자사주 환원률이 높고 과도한 밸류에이션이 아닌 종목을 선별합니다.',
    reference: 'Shareholder yield',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'shareholder_yield_filter', params: { min_yield_pct: 2.0 } },
      { condition_type: 'buyback_yield_filter', params: { min_yield_pct: 1.0 } },
      { condition_type: 'ev_to_ebitda_ratio', params: { max_ratio: 12 } },
    ]),
  },
  {
    key: 'deep_value_reversion',
    category: 'fundamental',
    name: '딥밸류 리버전',
    description: '저PBR/저PS 구간에서 회복 가능성이 높은 종목을 찾습니다.',
    reference: 'Deep value mean reversion',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'pb_ratio', params: { min_pb: 0, max_pb: 1.0, exclude_negative_bv: true } },
      { condition_type: 'ps_ratio', params: { min_ps: 0, max_ps: 1.5 } },
      { condition_type: 'price_change', params: { min_change_pct: -15, max_change_pct: 5, days: 20 } },
    ]),
  },
  {
    key: 'profitability_value_screen',
    category: 'fundamental',
    name: '수익성 + 밸류 스크린',
    description: '밸류와 수익성 지표를 동시에 만족하는 종목을 선별합니다.',
    reference: 'Profitability value blend',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'pe_ratio', params: { min_pe: 0, max_pe: 18 } },
      { condition_type: 'operating_margin', params: { min_margin_pct: 12 } },
      { condition_type: 'gross_profitability', params: { min_ratio: 0.2 } },
    ]),
  },
  {
    key: 'defensive_balance_sheet',
    category: 'fundamental',
    name: '재무안정 방어형',
    description: '낮은 부채비율과 높은 유동비율의 안정 종목을 찾습니다.',
    reference: 'Defensive balance sheet filter',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'debt_to_equity', params: { min_de: 0, max_de: 80 } },
      { condition_type: 'current_ratio', params: { min_ratio: 1.5, max_ratio: 5.0 } },
      { condition_type: 'roe', params: { min_roe: 8, max_roe: 100 } },
    ]),
  },
  {
    key: 'analyst_revision_momentum',
    category: 'fundamental',
    name: '애널리스트 상향 모멘텀',
    description: '실적 추정치 상향 종목과 가격 모멘텀을 결합합니다.',
    reference: 'Analyst revision momentum',
    graph: buildLinearGraph('SP500,NASDAQ100', [
      { condition_type: 'analyst_revision_1m', params: { min_revision_pct: 2 } },
      { condition_type: 'momentum_12_1', params: { lookback_months: 12, skip_recent_months: 1, min_return_pct: 6 } },
    ]),
  },
];
