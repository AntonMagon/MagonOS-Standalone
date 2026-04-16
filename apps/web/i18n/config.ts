export const locales = ["ru"] as const;
export type AppLocale = (typeof locales)[number];
export const defaultLocale: AppLocale = "ru";
