import type {Metadata} from 'next';
import type {ReactNode} from 'react';
import {NextIntlClientProvider} from 'next-intl';
import {getLocale, getMessages, getTranslations} from 'next-intl/server';

import {SiteHeader} from '@/components/navigation/site-header';
import {AppearanceProvider} from '@/components/personalization/appearance-provider';
import {ThemeProvider} from '@/components/providers/theme-provider';
import {fontBody, fontHeading, fontMono} from '@/lib/fonts';
import '@/app/globals.css';

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('meta');

  return {
    title: t('title'),
    description: t('description')
  };
}

export default async function RootLayout({children}: Readonly<{children: ReactNode}>) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale} suppressHydrationWarning>
      <body className={`${fontBody.variable} ${fontHeading.variable} ${fontMono.variable}`}>
        <NextIntlClientProvider locale={locale} messages={messages}>
          <ThemeProvider>
            <AppearanceProvider>
              <div className="relative min-h-screen pb-10">
                <SiteHeader />
                {children}
              </div>
            </AppearanceProvider>
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
