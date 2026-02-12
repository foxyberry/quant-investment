export const queryKeys = {
  portfolio: {
    all: ['portfolio'] as const,
    holdings: () => [...queryKeys.portfolio.all, 'holdings'] as const,
    summary: () => [...queryKeys.portfolio.all, 'summary'] as const,
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
    reports: (limit?: number) => [...queryKeys.analysis.all, 'reports', limit] as const,
    reportDetail: (date: string) =>
      [...queryKeys.analysis.all, 'report', date] as const,
    ticker: (ticker: string, period?: string) =>
      [...queryKeys.analysis.all, 'ticker', ticker, period] as const,
  },
  market: {
    all: ['market'] as const,
    search: (query: string) => [...queryKeys.market.all, 'search', query] as const,
  },
} as const;
