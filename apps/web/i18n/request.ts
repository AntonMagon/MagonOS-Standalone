import {cookies, headers} from 'next/headers';
import {getRequestConfig} from 'next-intl/server';

import {defaultLocale, isLocale, localeCookieName, type AppLocale} from '@/i18n/config';

type MessageTree = Record<string, unknown>;

function deepMerge(base: MessageTree, override: MessageTree): MessageTree {
  const result: MessageTree = {...base};

  for (const [key, value] of Object.entries(override)) {
    const baseValue = result[key];
    if (isPlainObject(baseValue) && isPlainObject(value)) {
      result[key] = deepMerge(baseValue, value);
      continue;
    }
    result[key] = value;
  }

  return result;
}

function isPlainObject(value: unknown): value is MessageTree {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

async function detectLocale(): Promise<AppLocale> {
  const cookieStore = await cookies();
  const cookieLocale = cookieStore.get(localeCookieName)?.value;
  if (isLocale(cookieLocale)) {
    return cookieLocale;
  }

  const acceptLanguage = (await headers()).get('accept-language') ?? '';
  const normalized = acceptLanguage.toLowerCase();
  if (normalized.startsWith('en')) {
    return 'en';
  }

  return defaultLocale;
}

async function loadMessages(locale: AppLocale) {
  const baseMessages = (await import('../messages/ru.json')).default as MessageTree;
  if (locale === defaultLocale) {
    return baseMessages;
  }

  const localeMessages = (await import(`../messages/${locale}.json`)).default as MessageTree;
  return deepMerge(baseMessages, localeMessages);
}

export default getRequestConfig(async () => {
  const locale = await detectLocale();

  return {
    locale,
    messages: await loadMessages(locale)
  };
});
