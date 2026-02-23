'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { Plus, RefreshCw, TrendingUp, TrendingDown, DollarSign, PieChart, Upload, Download, Search } from 'lucide-react';
import { Button, Card } from '@/components/ui';
import {
  HoldingsTable,
  AddHoldingModal,
  EditHoldingModal,
  DeleteConfirmModal,
  SellSignalBanner,
  CsvImportModal,
} from '@/components/portfolio';
import {
  getHoldings,
  addHolding,
  updateHolding,
  deleteHolding,
  getPortfolioSummary,
  getSellSignals,
  exportHoldingsCsv,
} from '@/lib/api';
import type { Holding, HoldingCreate, HoldingUpdate, PortfolioSummary, SellSignal } from '@/lib/types';
import { formatCurrency as formatCurrencyUtil, formatPercent as formatPercentUtil } from '@/lib/format';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import type { BaseCurrency } from '@/lib/format';

type FilterTab = 'all' | 'us' | 'kr' | 'etf';

/**
 * Portfolio summary card component
 */
interface SummaryCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  subValue?: string;
  iconBgClass?: string;
}

function SummaryCard({ title, value, icon, trend, subValue, iconBgClass = 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' }: SummaryCardProps) {
  const trendColorClass =
    trend === 'up'
      ? 'text-green-600 dark:text-green-400'
      : trend === 'down'
      ? 'text-red-600 dark:text-red-400'
      : 'text-[var(--foreground)]';

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center gap-4">
        <div className={`rounded-xl p-2.5 ${iconBgClass}`}>
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-[var(--foreground-muted)]">{title}</p>
          <p className={`text-lg font-semibold font-mono truncate ${trendColorClass}`}>
            {value}
          </p>
          {subValue && (
            <p className={`text-sm font-mono ${trendColorClass}`}>
              {subValue}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Portfolio page component
 */
export default function PortfolioPage() {
  const t = useTranslations('portfolio');
  const locale = useLocale();
  const { settings, updateBaseCurrency } = useUserSettings();
  const formatCurrency = (value: number, currency?: string) => formatCurrencyUtil(value, currency, locale);
  const formatPercent = (value: number) => formatPercentUtil(value);

  // Data state
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [sellSignals, setSellSignals] = useState<SellSignal[]>([]);

  // Loading state
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [selectedHolding, setSelectedHolding] = useState<Holding | null>(null);

  // CSV import modal state
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);

  // Sell signal banner state
  const [isBannerDismissed, setIsBannerDismissed] = useState(false);

  // Last refresh timestamp
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);

  // Filter state
  const [activeFilter, setActiveFilter] = useState<FilterTab>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Quick currency toggle
  const quickCurrencies: BaseCurrency[] = ['USD', 'KRW'];

  /**
   * Fetch all portfolio data
   */
  const fetchData = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setIsLoading(true);
    } else {
      setIsRefreshing(true);
    }
    setError(null);

    try {
      const [holdingsData, summaryData, signalsData] = await Promise.all([
        getHoldings(),
        getPortfolioSummary(settings.baseCurrency),
        getSellSignals(),
      ]);

      setHoldings(holdingsData);
      setSummary(summaryData);
      setSellSignals(signalsData);
      setIsBannerDismissed(false);
      setLastRefreshedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load portfolio data');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [settings.baseCurrency]);

  // Initial data fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /**
   * Filter holdings based on active filter tab and search query
   */
  const filteredHoldings = useMemo(() => {
    let filtered = holdings;

    // Apply category filter
    if (activeFilter === 'us') {
      filtered = filtered.filter((h) => h.currency === 'USD');
    } else if (activeFilter === 'kr') {
      filtered = filtered.filter((h) => h.currency === 'KRW');
    } else if (activeFilter === 'etf') {
      filtered = filtered.filter((h) =>
        h.ticker.includes('.') === false &&
        (h.name?.toLowerCase().includes('etf') || h.ticker.length >= 3)
      );
    }

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (h) =>
          h.ticker.toLowerCase().includes(query) ||
          (h.name && h.name.toLowerCase().includes(query))
      );
    }

    return filtered;
  }, [holdings, activeFilter, searchQuery]);

  /**
   * Handle adding a new holding
   */
  const handleAddHolding = useCallback(async (data: HoldingCreate) => {
    const newHolding = await addHolding(data);
    setHoldings((prev) => [...prev, newHolding]);
    fetchData(false);
  }, [fetchData]);

  /**
   * Handle updating a holding
   */
  const handleUpdateHolding = useCallback(async (ticker: string, data: HoldingUpdate) => {
    const updatedHolding = await updateHolding(ticker, data);
    setHoldings((prev) =>
      prev.map((h) => (h.ticker === ticker ? updatedHolding : h))
    );
    fetchData(false);
  }, [fetchData]);

  /**
   * Handle deleting a holding
   */
  const handleDeleteHolding = useCallback(async (ticker: string) => {
    await deleteHolding(ticker);
    setHoldings((prev) => prev.filter((h) => h.ticker !== ticker));
    fetchData(false);
  }, [fetchData]);

  const handleEditClick = useCallback((holding: Holding) => {
    setSelectedHolding(holding);
    setIsEditModalOpen(true);
  }, []);

  const handleDeleteClick = useCallback((holding: Holding) => {
    setSelectedHolding(holding);
    setIsDeleteModalOpen(true);
  }, []);

  const handleRowClick = useCallback((holding: Holding) => {
    const width = 900;
    const height = 700;
    const left = (screen.width - width) / 2;
    const top = (screen.height - height) / 2;
    window.open(
      `/${locale}/analysis/${encodeURIComponent(holding.ticker)}?popup=true`,
      `analysis_${holding.ticker}`,
      `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`
    );
  }, [locale]);

  const getPnlTrend = (value: number): 'up' | 'down' | 'neutral' => {
    if (value > 0) return 'up';
    if (value < 0) return 'down';
    return 'neutral';
  };

  const filterTabs: { key: FilterTab; labelKey: string }[] = [
    { key: 'all', labelKey: 'filterAll' },
    { key: 'us', labelKey: 'filterUS' },
    { key: 'kr', labelKey: 'filterKR' },
    { key: 'etf', labelKey: 'filterETF' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold text-[var(--foreground)]">{t('title')}</h1>
            {/* Currency quick-toggle */}
            <div className="flex items-center gap-1">
              <span className="text-xs text-[var(--foreground-muted)] mr-1">{t('baseCurrency')}</span>
              <div className="flex gap-0.5 rounded-lg bg-[var(--background)] p-0.5">
                {quickCurrencies.map((cur) => (
                  <button
                    key={cur}
                    type="button"
                    onClick={() => updateBaseCurrency(cur)}
                    className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                      settings.baseCurrency === cur
                        ? 'bg-[var(--background-secondary)] text-[var(--foreground)] shadow-sm'
                        : 'text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
                    }`}
                  >
                    {cur}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <p className="mt-1 text-[var(--foreground-muted)]">
            {t('subtitle')}
          </p>
        </div>
        <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
          {/* Last updated timestamp */}
          {lastRefreshedAt && (
            <span className="text-xs text-[var(--foreground-muted)]">
              {t('lastUpdated', {
                time: new Intl.DateTimeFormat(locale, {
                  hour: '2-digit',
                  minute: '2-digit',
                }).format(lastRefreshedAt),
              })}
            </span>
          )}
          <Button
            variant="outline"
            onClick={() => fetchData(false)}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            {t('refresh')}
          </Button>
          <Button variant="outline" onClick={() => setIsImportModalOpen(true)}>
            <Upload className="h-4 w-4 mr-2" />
            {t('importCsv')}
          </Button>
          <Button variant="outline" onClick={() => exportHoldingsCsv()}>
            <Download className="h-4 w-4 mr-2" />
            {t('exportCsv')}
          </Button>
          <Button variant="primary" onClick={() => setIsAddModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            {t('addHolding')}
          </Button>
        </div>
      </div>

      {/* Sell Signal Banner */}
      {!isBannerDismissed && sellSignals.length > 0 && (
        <SellSignalBanner
          signals={sellSignals}
          onDismiss={() => setIsBannerDismissed(true)}
        />
      )}

      {/* Error State */}
      {error && (
        <div className="rounded-xl border border-red-300 bg-red-50 p-4 text-red-700 dark:border-red-800 dark:bg-red-950/50 dark:text-red-300">
          <p className="font-medium">{t('errorLoading')}</p>
          <p className="text-sm mt-1">{error}</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData()}
            className="mt-3"
          >
            {t('refresh')}
          </Button>
        </div>
      )}

      {/* Portfolio Summary */}
      {!isLoading && summary && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryCard
            title={t('totalInvestment')}
            value={formatCurrency(summary.total_investment, summary.currency)}
            icon={<DollarSign className="h-4 w-4" />}
            iconBgClass="bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400"
          />
          <SummaryCard
            title={t('marketValue')}
            value={formatCurrency(summary.total_market_value, summary.currency)}
            icon={<PieChart className="h-4 w-4" />}
            iconBgClass="bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400"
          />
          <SummaryCard
            title={t('totalPnl')}
            value={formatCurrency(summary.total_pnl, summary.currency)}
            icon={
              summary.total_pnl >= 0 ? (
                <TrendingUp className="h-4 w-4" />
              ) : (
                <TrendingDown className="h-4 w-4" />
              )
            }
            trend={getPnlTrend(summary.total_pnl)}
            subValue={formatPercent(summary.total_pnl_pct)}
            iconBgClass={
              summary.total_pnl >= 0
                ? 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400'
                : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
            }
          />
          <SummaryCard
            title={t('holdings')}
            value={summary.holdings_count.toString()}
            icon={<PieChart className="h-4 w-4" />}
            iconBgClass="bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400"
          />
        </div>
      )}

      {/* Search + Filter */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* Filter Tabs */}
        <div className="flex gap-1 rounded-lg bg-[var(--background)] p-1">
          {filterTabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveFilter(tab.key)}
              className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                activeFilter === tab.key
                  ? 'bg-[var(--background-secondary)] text-[var(--foreground)] shadow-sm'
                  : 'text-[var(--foreground-muted)] hover:text-[var(--foreground)]'
              }`}
            >
              {t(tab.labelKey)}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--foreground-muted)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('search')}
            className="w-full sm:w-64 rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] pl-10 pr-4 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
          />
        </div>
      </div>

      {/* Holdings Table */}
      <Card title={t('holdings')} padding="none">
        <HoldingsTable
          holdings={filteredHoldings}
          isLoading={isLoading}
          onRowClick={handleRowClick}
          onEdit={handleEditClick}
          onDelete={handleDeleteClick}
        />
      </Card>

      {/* Add Holding Modal */}
      <AddHoldingModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAdd={handleAddHolding}
      />

      {/* Edit Holding Modal */}
      <EditHoldingModal
        isOpen={isEditModalOpen}
        holding={selectedHolding}
        onClose={() => {
          setIsEditModalOpen(false);
          setSelectedHolding(null);
        }}
        onUpdate={handleUpdateHolding}
      />

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={isDeleteModalOpen}
        holding={selectedHolding}
        onClose={() => {
          setIsDeleteModalOpen(false);
          setSelectedHolding(null);
        }}
        onConfirm={handleDeleteHolding}
      />

      {/* CSV Import Modal */}
      <CsvImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onImportComplete={() => fetchData(false)}
      />
    </div>
  );
}
