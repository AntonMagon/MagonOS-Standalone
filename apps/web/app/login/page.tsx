// RU: Файл входит в проверенный контур первой волны.
import {FoundationLoginForm} from "@/components/auth/foundation-login-form";

// RU: Login page должна завершать вход переводом в рабочий контур по роли, а не оставлять пользователя на token-screen.
export default function LoginPage() {
  return (
    <main className="container py-10">
      <section className="hero-shell rounded-[2.4rem] border border-white/12 px-6 py-7 shadow-panel md:px-8 md:py-8 lg:px-10">
        <div className="max-w-3xl space-y-3">
          <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Вход в платформу</div>
          <h1 className="text-4xl leading-tight">Открой свой рабочий раздел без лишних экранов</h1>
          {/* RU: Этот экран должен объяснять только вход и следующий рабочий маршрут, без debug-панелей и token dump. */}
          <p className="text-sm leading-7 text-muted-foreground">
            Здесь можно войти под тестовой ролью и сразу попасть в нужный раздел: заявки, заказы, поставщики или админ-настройки.
          </p>
        </div>
      </section>

      <section className="pt-8">
        <FoundationLoginForm />
      </section>
    </main>
  );
}
