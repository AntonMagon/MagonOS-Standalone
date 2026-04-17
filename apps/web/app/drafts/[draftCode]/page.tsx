// RU: Файл входит в проверенный контур первой волны.
import {DraftEditor} from "@/components/requests/draft-editor";

export default async function DraftPage({params}: {params: Promise<{draftCode: string}>}) {
  const {draftCode} = await params;
  return <DraftEditor draftCode={draftCode} />;
}
