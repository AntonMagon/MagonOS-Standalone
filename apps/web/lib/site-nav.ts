// RU: Держим nav как literal-массив и кастуем Route только в рендере, чтобы новый экран можно было подключать без ломки typed-route инференса.
export const siteNav = [
  { href: "/", labelKey: "overview" },
  { href: "/dashboard", labelKey: "dashboard" },
  { href: "/ops-workbench", labelKey: "ops" },
  { href: "/project-map", labelKey: "projectMap" },
  { href: "/personalize", labelKey: "personalize" }
] as const;
