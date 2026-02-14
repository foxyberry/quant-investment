'use client';

import { useState, useEffect, useCallback } from 'react';
import { Plus, RefreshCw, TrendingUp, TrendingDown, DollarSign, PieChart } from 'lucide-react';
import { Button, Card } from '@/components/ui';
import {
  HoldingsTable,
  AddHoldingModal,
  EditHoldingModal,
  DeleteConfirmModal,
  SellSignalBanner,
} from '@/components/portfolio';
import {
  getHoldings,
  addHolding,
  updateHolding,
  deleteHolding,
  getPortfolioSummary,
  getSellSignals,
} from '@/lib/api';
import type { Holding, HoldingCreate, HoldingUpdate, PortfolioSummary, SellSignal } from '@/lib/types';

/**
 * Format a number as currency
 */
function formatCurrency(value: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format a number as percentage
 */
function formatPercent(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

/**
 * Portfolio summary card component
 */
interface SummaryCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  subValue?: string;
}

function SummaryCard({ title, value, icon, trend, subValue }: SummaryCardProps) {
  const trendColorClass =
    trend === 'up'
      ? 'text-green-600 dark:text-green-400'
      : trend === 'down'
      ? 'text-red-600 dark:text-red-400'
      : 'text-[var(--foreground)]';

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--background-secondary)] p-4">
      <div className="flex items-center gap-3">
        <div className="rounded-full bg-[var(--background)] p-2 text-[var(--color-primary)]">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-[var(--foreground-muted)]">{title}</p>
          <p className={`text-xl font-semibold font-mono truncate ${trendColorClass}`}>
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

  // Sell signal banner state
  const [isBannerDismissed, setIsBannerDismissed] = useState(false);

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
        getPortfolioSummary(),
        getSellSignals(),
      ]);

      setHoldings(holdingsData);
      setSummary(summaryData);
      setSellSignals(signalsData);
      setIsBannerDismissed(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load portfolio data');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  // Initial data fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /**
   * Handle adding a new holding
   */
  const handleAddHolding = useCallback(async (data: HoldingCreate) => {
    const newHolding = await addHolding(data);
    // Optimistically add to list
    setHoldings((prev) => [...prev, newHolding]);
    // Refresh to get updated summary
    fetchData(false);
  }, [fetchData]);

  /**
   * Handle updating a holding
   */
  const handleUpdateHolding = useCallback(async (ticker: string, data: HoldingUpdate) => {
    const updatedHolding = await updateHolding(ticker, data);
    // Optimistically update in list
    setHoldings((prev) =>
      prev.map((h) => (h.ticker === ticker ? updatedHolding : h))
    );
    // Refresh to get updated summary
    fetchData(false);
  }, [fetchData]);

  /**
   * Handle deleting a holding
   */
  const handleDeleteHolding = useCallback(async (ticker: string) => {
    await deleteHolding(ticker);
    // Optimistically remove from list
    setHoldings((prev) => prev.filter((h) => h.ticker !== ticker));
    // Refresh to get updated summary
    fetchData(false);
  }, [fetchData]);

  /**
   * Open edit modal
   */
  const handleEditClick = useCallback((holding: Holding) => {
    setSelectedHolding(holding);
    setIsEditModalOpen(true);
  }, []);

  /**
   * Open delete confirmation modal
   */
  const handleDeleteClick = useCallback((holding: Holding) => {
    setSelectedHolding(holding);
    setIsDeleteModalOpen(true);
  }, []);

  // Calculate trend based on P&L
  const getPnlTrend = (value: number): 'up' | 'down' | 'neutral' => {
    if (value > 0) return 'up';
    if (value < 0) return 'down';
    return 'neutral';
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">Portfolio</h1>
          <p className="mt-1 text-[var(--foreground-muted)]">
            Manage your holdings and track performance
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={() => fetchData(false)}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="primary" onClick={() => setIsAddModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Holding
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
        <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-700 dark:border-red-800 dark:bg-red-950/50 dark:text-red-300">
          <p className="font-medium">Error loading portfolio</p>
          <p className="text-sm mt-1">{error}</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData()}
            className="mt-3"
          >
            Try Again
          </Button>
        </div>
      )}

      {/* Portfolio Summary */}
      {!isLoading && summary && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryCard
            title="Total Investment"
            value={formatCurrency(summary.total_investment, summary.currency)}
            icon={<DollarSign className="h-5 w-5" />}
          />
          <SummaryCard
            title="Market Value"
            value={formatCurrency(summary.total_market_value, summary.currency)}
            icon={<PieChart className="h-5 w-5" />}
          />
          <SummaryCard
            title="Total P&L"
            value={formatCurrency(summary.total_pnl, summary.currency)}
            icon={
              summary.total_pnl >= 0 ? (
                <TrendingUp className="h-5 w-5" />
              ) : (
                <TrendingDown className="h-5 w-5" />
              )
            }
            trend={getPnlTrend(summary.total_pnl)}
            subValue={formatPercent(summary.total_pnl_pct)}
          />
          <SummaryCard
            title="Holdings"
            value={summary.holdings_count.toString()}
            icon={<PieChart className="h-5 w-5" />}
          />
        </div>
      )}

      {/* Holdings Table */}
      <Card title="Holdings" padding="none">
        <HoldingsTable
          holdings={holdings}
          isLoading={isLoading}
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
    </div>
  );
}
