// RU: Файл входит в проверенный контур первой волны.
import {OrderDetailView} from "@/components/orders/order-detail";

export default async function OrderDetailPage({params}: {params: Promise<{orderCode: string}>}) {
  const {orderCode} = await params;
  return <OrderDetailView orderCode={orderCode} />;
}
