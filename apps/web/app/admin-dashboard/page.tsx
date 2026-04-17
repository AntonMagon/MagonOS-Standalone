import {AdminDashboardView} from "@/components/dashboard/foundation-dashboards";

export default function AdminDashboardPage() {
  // RU: Страница держит отдельный admin route, чтобы ролевой доступ к панели не зависел от клиентских экранов.
  return <AdminDashboardView />;
}
