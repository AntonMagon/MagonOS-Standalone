// RU: Файл входит в проверенный контур первой волны.
import {FoundationLoginForm} from "@/components/auth/foundation-login-form";

export default function LoginPage() {
  return (
    <main className="container py-10">
      <section className="hero-shell rounded-[2.4rem] border border-white/12 px-6 py-7 shadow-panel md:px-8 md:py-8 lg:px-10">
        <div className="max-w-3xl space-y-3">
          <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Wave1 foundation</div>
          <h1 className="text-4xl leading-tight">Login и базовый role/session контур</h1>
          <p className="text-sm leading-7 text-muted-foreground">
            Этот экран предназначен для smoke-проверки foundation skeleton: seed-пользователи, выдача session token и базовая authz для ролей `guest / customer / operator / admin`.
          </p>
        </div>
      </section>

      <section className="pt-8">
        <FoundationLoginForm />
      </section>
    </main>
  );
}
