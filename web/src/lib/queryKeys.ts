export const queryKeys = {
  portfolio: {
    all: ['portfolio'] as const,
    holdings: () => [...queryKeys.portfolio.all, 'holdings'] as const,
    summary: (baseCurrency?: string) => [...queryKeys.portfolio.all, 'summary', baseCurrency] as const,
    sellSignals: () => [...queryKeys.portfolio.all, 'sell-signals'] as const,
  },
  screening: {
    all: ['screening'] as const,
    presets: () => [...queryKeys.screening.all, 'presets'] as const,
    universes: () => [...queryKeys.screening.all, 'universes'] as const,
    results: (preset: string, universe: string) =>
      [...queryKeys.screening.all, 'results', preset, universe] as const,
  },
  analysis: {
    all: ['analysis'] as const,
    ticker: (ticker: string, period?: string) =>
      [...queryKeys.analysis.all, 'ticker', ticker, period] as const,
  },
  market: {
    all: ['market'] as const,
    search: (query: string) => [...queryKeys.market.all, 'search', query] as const,
  },
  strategy: {
    all: ['strategy'] as const,
    conditions: () => [...queryKeys.strategy.all, 'conditions'] as const,
    saved: () => [...queryKeys.strategy.all, 'saved'] as const,
    detail: (id: string) => [...queryKeys.strategy.all, 'saved', id] as const,
  },
  backtest: {
    all: ['backtest'] as const,
    strategies: () => [...queryKeys.backtest.all, 'strategies'] as const,
  },
} as const;
