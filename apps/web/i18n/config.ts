export const locales = ['ru', 'en'] as const;
export type AppLocale = (typeof locales)[number];

export const defaultLocale: AppLocale = 'ru';
export const localeCookieName = 'magonos-locale';

export function isLocale(value: string | undefined | null): value is AppLocale {
  return Boolean(value && locales.includes(value as AppLocale));
}
