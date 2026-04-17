import {OperatorWorkbenchView} from "@/components/dashboard/foundation-dashboards";

export default function OpsWorkbenchPage() {
  // RU: Отдельный route для operator workbench нужен для явной role-boundary и прямых smoke-проверок.
  return <OperatorWorkbenchView />;
}
