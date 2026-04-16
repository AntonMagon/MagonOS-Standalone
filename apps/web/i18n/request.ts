import {getRequestConfig} from 'next-intl/server';

import {defaultLocale, locales, type AppLocale} from '@/i18n/config';

async function loadMessages(locale: AppLocale) {
  return (await import(`../messages/${locale}.json`)).default;
}

export default getRequestConfig(async () => {
  const locale = locales.includes(defaultLocale) ? defaultLocale : 'ru';

  return {
    locale,
    messages: await loadMessages(locale)
  };
});
