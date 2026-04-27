import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages, getTranslations } from 'next-intl/server';
import { notFound } from 'next/navigation';
import { routing } from '@/i18n/routing';
import '../globals.css';
import MainLayout from '@/features/layout/MainLayout';
import QueryProvider from '@/providers/QueryProvider';
import { UserSettingsProvider } from '@/contexts/UserSettingsContext';
import AgentationProvider from '@/features/dev/AgentationProvider';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

type MetadataProps = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: MetadataProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'common' });

  return {
    title: t('siteTitle'),
    description: t('siteDescription'),
    keywords: ['quant', 'investment', 'trading', 'portfolio', 'analysis'],
    icons: { icon: '/favicon.ico' },
  };
}

type Props = {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
};

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;

  if (!routing.locales.includes(locale as (typeof routing.locales)[number])) {
    notFound();
  }

  const messages = await getMessages();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <NextIntlClientProvider messages={messages}>
          <QueryProvider>
            <UserSettingsProvider>
              <MainLayout>{children}</MainLayout>
              <AgentationProvider />
            </UserSettingsProvider>
          </QueryProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
