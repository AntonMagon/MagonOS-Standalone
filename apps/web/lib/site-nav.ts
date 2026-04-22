// RU: Файл входит в проверенный контур первой волны.
// RU: Держим nav как literal-массив и кастуем Route только в рендере, чтобы новый экран можно было подключать без ломки typed-route инференса.
// RU: Admin-config живёт в том же nav-слое, потому что базовая business configuration теперь является частью продукта.
export const siteNav = [
  { href: "/", labelKey: "overview" },
  { href: "/marketing", labelKey: "marketing" },
  { href: "/catalog", labelKey: "catalog" },
  { href: "/request-workbench", labelKey: "requests" },
  { href: "/orders", labelKey: "orders" },
  { href: "/dashboard", labelKey: "dashboard" },
  { href: "/suppliers", labelKey: "suppliers" },
  { href: "/ops-workbench", labelKey: "ops" },
  { href: "/admin-config", labelKey: "adminConfig" },
  { href: "/login", labelKey: "login" },
  { href: "/project-map", labelKey: "projectMap" },
  // RU: Справка остаётся во вторичном nav-слое, чтобы header не разрастался, но контекст проекта был доступен прямо из shell.
  { href: "/reference", labelKey: "reference" },
  { href: "/personalize", labelKey: "personalize" }
] as const;
