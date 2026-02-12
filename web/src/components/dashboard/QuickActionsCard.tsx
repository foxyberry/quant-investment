'use client';

import Link from 'next/link';
import { Card, Button } from '@/components/ui';
import { Search, BarChart3, Briefcase, Settings } from 'lucide-react';

interface QuickAction {
  label: string;
  description: string;
  href: string;
  icon: typeof Search;
  variant: 'primary' | 'secondary' | 'outline';
}

const quickActions: QuickAction[] = [
  {
    label: 'Run Screening',
    description: 'Find stocks matching your criteria',
    href: '/screening',
    icon: Search,
    variant: 'primary',
  },
  {
    label: 'View Analysis',
    description: 'Browse analysis reports',
    href: '/analysis',
    icon: BarChart3,
    variant: 'secondary',
  },
  {
    label: 'Portfolio',
    description: 'Manage your holdings',
    href: '/portfolio',
    icon: Briefcase,
    variant: 'outline',
  },
  {
    label: 'Settings',
    description: 'Configure preferences',
    href: '/settings',
    icon: Settings,
    variant: 'outline',
  },
];

/**
 * Quick action buttons for common tasks
 */
export default function QuickActionsCard() {
  return (
    <Card title="Quick Actions">
      <div className="grid gap-3 sm:grid-cols-2">
        {quickActions.map((action) => {
          const Icon = action.icon;

          return (
            <Link key={action.label} href={action.href} className="block">
              <Button
                variant={action.variant}
                fullWidth
                className="justify-start gap-3 h-auto py-3"
              >
                <Icon className="h-5 w-5 flex-shrink-0" />
                <div className="text-left">
                  <div className="font-medium">{action.label}</div>
                  <div className="text-xs opacity-80">{action.description}</div>
                </div>
              </Button>
            </Link>
          );
        })}
      </div>
    </Card>
  );
}
