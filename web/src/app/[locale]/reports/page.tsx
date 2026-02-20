'use client';

import { useTranslations } from 'next-intl';
import { FileText } from 'lucide-react';
import { ReportList } from '@/components/analysis';

/**
 * Dedicated page for analysis reports.
 */
export default function ReportsPage() {
  const t = useTranslations('reports');

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center gap-3">
        <FileText className="h-7 w-7 text-[var(--color-primary)]" />
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">
            {t('title')}
          </h1>
          <p className="mt-1 text-[var(--foreground-muted)]">
            {t('subtitle')}
          </p>
        </div>
      </div>

      {/* Reports List */}
      <ReportList initialLimit={20} />
    </div>
  );
}
