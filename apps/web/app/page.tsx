// RU: Главная страница теперь работает как продуктовый poster-screen и ведёт в реальные рабочие поверхности без фейкового dashboard-шума.
import {RetroPrintLanding} from '@/components/home/retro-print-landing';
import {getPlatformStatus} from '@/lib/standalone-api';

export default async function HomePage() {
  const platformStatus = await getPlatformStatus();
  return <RetroPrintLanding platformStatus={platformStatus} />;
}
