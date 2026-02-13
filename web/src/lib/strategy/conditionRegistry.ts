export interface ConditionParam {
  name: string;
  type: 'int' | 'float' | 'str' | 'bool';
  default: unknown;
  description: string;
}

export interface ConditionMeta {
  key: string;
  label: string;
  description: string;
  category: string;
  params: ConditionParam[];
}

export const CATEGORIES = [
  'Price',
  'Volume',
  'Moving Average',
  'RSI',
  'Accumulation',
  'Breakout',
] as const;

export type Category = (typeof CATEGORIES)[number];

export const CONDITION_REGISTRY: ConditionMeta[] = [
  // Price
  {
    key: 'min_price',
    label: 'Min Price',
    description: 'Stock price >= threshold',
    category: 'Price',
    params: [{ name: 'min_price', type: 'float', default: 5000, description: 'Minimum price' }],
  },
  {
    key: 'max_price',
    label: 'Max Price',
    description: 'Stock price <= threshold',
    category: 'Price',
    params: [{ name: 'max_price', type: 'float', default: 100000, description: 'Maximum price' }],
  },
  {
    key: 'price_range',
    label: 'Price Range',
    description: 'Stock price within range',
    category: 'Price',
    params: [
      { name: 'min_price', type: 'float', default: 0, description: 'Min price' },
      { name: 'max_price', type: 'float', default: 999999, description: 'Max price' },
    ],
  },
  {
    key: 'price_change',
    label: 'Price Change %',
    description: 'Price change over N days',
    category: 'Price',
    params: [
      { name: 'min_change_pct', type: 'float', default: null, description: 'Min change %' },
      { name: 'max_change_pct', type: 'float', default: null, description: 'Max change %' },
      { name: 'days', type: 'int', default: 1, description: 'Period (days)' },
    ],
  },
  // Volume
  {
    key: 'min_volume',
    label: 'Min Volume',
    description: 'Volume >= threshold',
    category: 'Volume',
    params: [{ name: 'min_volume', type: 'int', default: 100000, description: 'Minimum volume' }],
  },
  {
    key: 'volume_above_avg',
    label: 'Volume Above Avg',
    description: 'Volume above moving average',
    category: 'Volume',
    params: [
      { name: 'multiplier', type: 'float', default: 1.5, description: 'Avg multiplier' },
      { name: 'period', type: 'int', default: 20, description: 'Average period' },
    ],
  },
  {
    key: 'volume_spike',
    label: 'Volume Spike',
    description: 'Sudden volume increase',
    category: 'Volume',
    params: [
      { name: 'multiplier', type: 'float', default: 2.0, description: 'Spike multiplier' },
      { name: 'period', type: 'int', default: 20, description: 'Average period' },
    ],
  },
  // Moving Average
  {
    key: 'ma_touch',
    label: 'MA Touch',
    description: 'Price near moving average',
    category: 'Moving Average',
    params: [
      { name: 'period', type: 'int', default: 20, description: 'MA period' },
      { name: 'threshold', type: 'float', default: 0.02, description: 'Touch threshold (ratio)' },
    ],
  },
  {
    key: 'above_ma',
    label: 'Above MA',
    description: 'Price above moving average',
    category: 'Moving Average',
    params: [
      { name: 'period', type: 'int', default: 20, description: 'MA period' },
      { name: 'min_distance_pct', type: 'float', default: 0, description: 'Min distance %' },
    ],
  },
  {
    key: 'below_ma',
    label: 'Below MA',
    description: 'Price below moving average',
    category: 'Moving Average',
    params: [
      { name: 'period', type: 'int', default: 20, description: 'MA period' },
      { name: 'max_distance_pct', type: 'float', default: 0, description: 'Max distance %' },
    ],
  },
  {
    key: 'ma_cross_up',
    label: 'MA Cross Up',
    description: 'Golden cross',
    category: 'Moving Average',
    params: [
      { name: 'short_period', type: 'int', default: 20, description: 'Short MA period' },
      { name: 'long_period', type: 'int', default: 60, description: 'Long MA period' },
      { name: 'lookback_days', type: 'int', default: 5, description: 'Lookback days' },
    ],
  },
  {
    key: 'ma_cross_down',
    label: 'MA Cross Down',
    description: 'Death cross',
    category: 'Moving Average',
    params: [
      { name: 'short_period', type: 'int', default: 20, description: 'Short MA period' },
      { name: 'long_period', type: 'int', default: 60, description: 'Long MA period' },
      { name: 'lookback_days', type: 'int', default: 5, description: 'Lookback days' },
    ],
  },
  // RSI
  {
    key: 'rsi_oversold',
    label: 'RSI Oversold',
    description: 'RSI below threshold',
    category: 'RSI',
    params: [
      { name: 'threshold', type: 'float', default: 30, description: 'RSI threshold' },
      { name: 'period', type: 'int', default: 14, description: 'RSI period' },
    ],
  },
  {
    key: 'rsi_overbought',
    label: 'RSI Overbought',
    description: 'RSI above threshold',
    category: 'RSI',
    params: [
      { name: 'threshold', type: 'float', default: 70, description: 'RSI threshold' },
      { name: 'period', type: 'int', default: 14, description: 'RSI period' },
    ],
  },
  {
    key: 'rsi_range',
    label: 'RSI Range',
    description: 'RSI within range',
    category: 'RSI',
    params: [
      { name: 'lower', type: 'float', default: 30, description: 'Lower bound' },
      { name: 'upper', type: 'float', default: 70, description: 'Upper bound' },
      { name: 'period', type: 'int', default: 14, description: 'RSI period' },
    ],
  },
  // Accumulation
  {
    key: 'bollinger_width',
    label: 'Bollinger Width',
    description: 'BB width contraction',
    category: 'Accumulation',
    params: [
      { name: 'max_width_pct', type: 'float', default: 10.0, description: 'Max BB width %' },
      { name: 'period', type: 'int', default: 20, description: 'BB period' },
      { name: 'std_dev', type: 'float', default: 2.0, description: 'Std deviation' },
    ],
  },
  {
    key: 'volume_below_avg',
    label: 'Volume Below Avg',
    description: 'Quiet volume zone',
    category: 'Accumulation',
    params: [
      { name: 'multiplier', type: 'float', default: 0.8, description: 'Max ratio to avg' },
      { name: 'period', type: 'int', default: 20, description: 'Average period' },
    ],
  },
  {
    key: 'price_flat',
    label: 'Price Flat',
    description: 'Price consolidation',
    category: 'Accumulation',
    params: [
      { name: 'max_range_pct', type: 'float', default: 5.0, description: 'Max range %' },
      { name: 'period', type: 'int', default: 20, description: 'Period' },
    ],
  },
  {
    key: 'obv_trend',
    label: 'OBV Trend',
    description: 'On-Balance Volume trend',
    category: 'Accumulation',
    params: [
      { name: 'direction', type: 'str', default: 'up', description: 'Trend direction (up/down)' },
      { name: 'lookback', type: 'int', default: 20, description: 'Lookback period' },
    ],
  },
  {
    key: 'stochastic_level',
    label: 'Stochastic Level',
    description: 'Stochastic oscillator level',
    category: 'Accumulation',
    params: [
      { name: 'threshold', type: 'float', default: 20.0, description: 'Level threshold' },
      { name: 'condition', type: 'str', default: 'below', description: 'below or above' },
      { name: 'k_period', type: 'int', default: 14, description: '%K period' },
      { name: 'd_period', type: 'int', default: 3, description: '%D period' },
    ],
  },
  {
    key: 'vpci_trend',
    label: 'VPCI Trend',
    description: 'VPCI trend direction',
    category: 'Accumulation',
    params: [
      { name: 'direction', type: 'str', default: 'up', description: 'Trend direction (up/down)' },
      { name: 'short_period', type: 'int', default: 5, description: 'Short period' },
      { name: 'long_period', type: 'int', default: 20, description: 'Long period' },
      { name: 'lookback', type: 'int', default: 10, description: 'Lookback period' },
    ],
  },
  {
    key: 'obv_divergence',
    label: 'OBV Divergence',
    description: 'Price flat + OBV rising',
    category: 'Accumulation',
    params: [
      { name: 'price_max_range_pct', type: 'float', default: 5.0, description: 'Price range %' },
      { name: 'obv_min_change_pct', type: 'float', default: 5.0, description: 'OBV change %' },
      { name: 'period', type: 'int', default: 20, description: 'Period' },
    ],
  },
  {
    key: 'stochastic_divergence',
    label: 'Stochastic Divergence',
    description: 'Bullish stochastic divergence',
    category: 'Accumulation',
    params: [
      { name: 'k_period', type: 'int', default: 14, description: '%K period' },
      { name: 'd_period', type: 'int', default: 3, description: '%D period' },
      { name: 'lookback', type: 'int', default: 20, description: 'Lookback period' },
      { name: 'divergence_threshold', type: 'float', default: 5.0, description: 'Threshold %' },
    ],
  },
  {
    key: 'vpci_divergence',
    label: 'VPCI Divergence',
    description: 'Price flat + VPCI rising',
    category: 'Accumulation',
    params: [
      { name: 'price_max_range_pct', type: 'float', default: 5.0, description: 'Price range %' },
      { name: 'short_period', type: 'int', default: 5, description: 'Short period' },
      { name: 'long_period', type: 'int', default: 20, description: 'Long period' },
      { name: 'lookback', type: 'int', default: 20, description: 'Lookback period' },
    ],
  },
  // Breakout
  {
    key: 'bottom_breakout',
    label: 'Bottom Breakout',
    description: 'N-day low breakout',
    category: 'Breakout',
    params: [
      { name: 'lookback_days', type: 'int', default: 20, description: 'Lookback days' },
      { name: 'breakout_pct', type: 'float', default: 5.0, description: 'Breakout %' },
    ],
  },
  {
    key: 'fresh_breakout',
    label: 'Fresh Breakout',
    description: 'First-time breakout',
    category: 'Breakout',
    params: [
      { name: 'lookback_days', type: 'int', default: 20, description: 'Lookback days' },
      { name: 'breakout_pct', type: 'float', default: 5.0, description: 'Breakout %' },
    ],
  },
  {
    key: 'breakout_with_volume',
    label: 'Breakout + Volume',
    description: 'Breakout with volume confirmation',
    category: 'Breakout',
    params: [
      { name: 'lookback_days', type: 'int', default: 20, description: 'Lookback days' },
      { name: 'breakout_pct', type: 'float', default: 5.0, description: 'Breakout %' },
      { name: 'volume_ratio', type: 'float', default: 1.5, description: 'Volume ratio' },
      { name: 'volume_avg_days', type: 'int', default: 10, description: 'Volume avg days' },
      { name: 'fresh_only', type: 'bool', default: true, description: 'Fresh breakout only' },
    ],
  },
  {
    key: 'resistance_breakout',
    label: 'Resistance Breakout',
    description: 'Resistance level breakout',
    category: 'Breakout',
    params: [
      { name: 'lookback_days', type: 'int', default: 20, description: 'Lookback days' },
      { name: 'breakout_margin_pct', type: 'float', default: 0.0, description: 'Margin above resistance %' },
    ],
  },
];

export function getConditionsByCategory(): Record<string, ConditionMeta[]> {
  const grouped: Record<string, ConditionMeta[]> = {};
  for (const cond of CONDITION_REGISTRY) {
    if (!grouped[cond.category]) {
      grouped[cond.category] = [];
    }
    grouped[cond.category].push(cond);
  }
  return grouped;
}

export function getConditionMeta(key: string): ConditionMeta | undefined {
  return CONDITION_REGISTRY.find((c) => c.key === key);
}

export function getDefaultParams(key: string): Record<string, unknown> {
  const meta = getConditionMeta(key);
  if (!meta) return {};
  const params: Record<string, unknown> = {};
  for (const p of meta.params) {
    params[p.name] = p.default;
  }
  return params;
}
