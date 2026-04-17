import {SupplyDashboardView} from "@/components/dashboard/foundation-dashboards";

export default function SupplyDashboardPage() {
  // RU: Supply-side панель живёт на отдельном маршруте для проверяемого доступа и независимого smoke-прохода.
  return <SupplyDashboardView />;
}
