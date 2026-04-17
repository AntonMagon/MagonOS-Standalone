// RU: Файл входит в проверенный контур первой волны.
import {CatalogDetail} from "@/components/catalog/catalog-detail";

export default async function CatalogItemPage({params}: {params: Promise<{itemCode: string}>}) {
  const {itemCode} = await params;
  return (
    <main className="container py-10">
      <CatalogDetail itemCode={itemCode} />
    </main>
  );
}
