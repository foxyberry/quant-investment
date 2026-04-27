'use client';

import { useTranslations } from 'next-intl';
import { Card, Button } from '@/components/ui';
import { Search, BarChart3, Briefcase, Settings } from 'lucide-react';
import { Link } from '@/i18n/navigation';

interface QuickAction {
  labelKey: string;
  descKey: string;
  href: '/' | '/screening' | '/analysis' | '/portfolio' | '/settings';
  icon: typeof Search;
  variant: 'primary' | 'secondary' | 'outline';
}

const quickActions: QuickAction[] = [
  {
    labelKey: 'runScreening',
    descKey: 'runScreeningDesc',
    href: '/screening',
    icon: Search,
    variant: 'primary',
  },
  {
    labelKey: 'viewAnalysis',
    descKey: 'viewAnalysisDesc',
    href: '/analysis',
    icon: BarChart3,
    variant: 'secondary',
  },
  {
    labelKey: 'portfolioAction',
    descKey: 'portfolioActionDesc',
    href: '/portfolio',
    icon: Briefcase,
    variant: 'outline',
  },
  {
    labelKey: 'settingsAction',
    descKey: 'settingsActionDesc',
    href: '/settings',
    icon: Settings,
    variant: 'outline',
  },
];

export default function QuickActionsCard() {
  const t = useTranslations('dashboard');

  return (
    <Card title={t('quickActions')}>
      <div className="grid gap-3 sm:grid-cols-2">
        {quickActions.map((action) => {
          const Icon = action.icon;

          return (
            <Link key={action.labelKey} href={action.href} className="block">
              <Button
                variant={action.variant}
                fullWidth
                className="justify-start gap-3 h-auto py-3"
              >
                <Icon className="h-5 w-5 flex-shrink-0" />
                <div className="text-left">
                  <div className="font-medium">{t(action.labelKey)}</div>
                  <div className="text-xs opacity-80">{t(action.descKey)}</div>
                </div>
              </Button>
            </Link>
          );
        })}
      </div>
    </Card>
  );
}
