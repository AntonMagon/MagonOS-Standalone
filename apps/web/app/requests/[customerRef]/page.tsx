// RU: Файл входит в проверенный контур первой волны.
import {RequestPublicView} from "@/components/requests/request-public-view";

export default async function RequestPage({params}: {params: Promise<{customerRef: string}>}) {
  const {customerRef} = await params;
  return (
    <main className="container py-10">
      <RequestPublicView customerRef={customerRef} />
    </main>
  );
}
