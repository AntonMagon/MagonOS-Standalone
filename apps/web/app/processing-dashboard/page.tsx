import {ProcessingDashboardView} from "@/components/dashboard/foundation-dashboards";

export default function ProcessingDashboardPage() {
  // RU: Processing dashboard вынесен отдельно, чтобы производственный срез не смешивался с admin/customer view.
  return <ProcessingDashboardView />;
}
