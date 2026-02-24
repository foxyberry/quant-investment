import type { StrategyGraph } from './graphSerializer';

export interface SampleStrategyPreset {
  key: string;
  name: string;
  description: string;
  graph: StrategyGraph;
}

export const SAMPLE_STRATEGY_PRESETS: SampleStrategyPreset[] = [
  {
    key: 'price_volume_breakout',
    name: '가격 범위 + 거래량 급증',
    description: '가격 구간과 거래량 급증을 동시에 만족하는 종목을 찾습니다.',
    graph: {
      nodes: [
        {
          id: 'sample_universe_1',
          data: { node_type: 'universe', universe: 'KOSPI,KOSDAQ' },
          position: { x: 60, y: 190 },
        },
        {
          id: 'sample_cond_1',
          data: {
            node_type: 'condition',
            condition_type: 'price_range',
            params: { min_price: 5000, max_price: 999999 },
          },
          position: { x: 330, y: 160 },
        },
        {
          id: 'sample_cond_2',
          data: {
            node_type: 'condition',
            condition_type: 'volume_above_avg',
            params: { multiplier: 1.5, period: 20 },
          },
          position: { x: 600, y: 160 },
        },
        {
          id: 'sample_output_1',
          data: { node_type: 'output' },
          position: { x: 900, y: 190 },
        },
      ],
      edges: [
        { id: 'sample_edge_1', source: 'sample_universe_1', target: 'sample_cond_1' },
        { id: 'sample_edge_2', source: 'sample_cond_1', target: 'sample_cond_2' },
        { id: 'sample_edge_3', source: 'sample_cond_2', target: 'sample_output_1' },
      ],
    },
  },
  {
    key: 'rsi_rebound_watch',
    name: 'RSI 과매도 반등',
    description: '과매도 구간의 RSI와 거래량 확인으로 반등 후보를 찾습니다.',
    graph: {
      nodes: [
        {
          id: 'sample2_universe_1',
          data: { node_type: 'universe', universe: 'SP500,NASDAQ100' },
          position: { x: 60, y: 190 },
        },
        {
          id: 'sample2_cond_1',
          data: {
            node_type: 'condition',
            condition_type: 'rsi_oversold',
            params: { threshold: 35, period: 14 },
          },
          position: { x: 330, y: 160 },
        },
        {
          id: 'sample2_cond_2',
          data: {
            node_type: 'condition',
            condition_type: 'volume_above_avg',
            params: { multiplier: 1.2, period: 20 },
          },
          position: { x: 600, y: 160 },
        },
        {
          id: 'sample2_output_1',
          data: { node_type: 'output' },
          position: { x: 900, y: 190 },
        },
      ],
      edges: [
        { id: 'sample2_edge_1', source: 'sample2_universe_1', target: 'sample2_cond_1' },
        { id: 'sample2_edge_2', source: 'sample2_cond_1', target: 'sample2_cond_2' },
        { id: 'sample2_edge_3', source: 'sample2_cond_2', target: 'sample2_output_1' },
      ],
    },
  },
];
