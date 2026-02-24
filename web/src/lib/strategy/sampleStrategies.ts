import type { StrategyGraph } from './graphSerializer';

export interface SampleStrategyPreset {
  key: string;
  name: string;
  description: string;
  reference?: string;
  graph: StrategyGraph;
}

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
    name: '단기 돌파 + 유동성 필터',
    description: '신규 고점 돌파와 충분한 거래량/거래대금을 동시에 확인합니다.',
    reference: 'Breakout + liquidity filter',
    graph: buildLinearGraph('KOSPI,KOSDAQ', [
      { condition_type: 'fresh_breakout', params: { lookback_days: 55, breakout_pct: 2 } },
      { condition_type: 'volume_spike', params: { multiplier: 2.0, period: 20 } },
      { condition_type: 'avg_trading_value', params: { lookback_days: 20, min_value: 5000000000 } },
    ]),
  },
];
