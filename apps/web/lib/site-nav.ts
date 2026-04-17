// RU: Файл входит в проверенный контур первой волны.
// RU: Держим nav как literal-массив и кастуем Route только в рендере, чтобы новый экран можно было подключать без ломки typed-route инференса.
export const siteNav = [
  { href: "/", labelKey: "overview" },
  { href: "/catalog", labelKey: "catalog" },
  { href: "/request-workbench", labelKey: "requests" },
  { href: "/orders", labelKey: "orders" },
  { href: "/dashboard", labelKey: "dashboard" },
  { href: "/suppliers", labelKey: "suppliers" },
  { href: "/ops-workbench", labelKey: "ops" },
  { href: "/login", labelKey: "login" },
  { href: "/project-map", labelKey: "projectMap" },
  { href: "/personalize", labelKey: "personalize" }
] as const;
