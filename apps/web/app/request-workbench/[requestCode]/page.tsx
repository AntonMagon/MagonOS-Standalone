// RU: Файл входит в проверенный контур первой волны.
import {RequestWorkbenchDetail} from "@/components/requests/request-workbench-detail";

export default async function RequestWorkbenchDetailPage({params}: {params: Promise<{requestCode: string}>}) {
  const {requestCode} = await params;
  return <RequestWorkbenchDetail requestCode={requestCode} />;
}
