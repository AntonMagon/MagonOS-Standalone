// RU: Файл входит в проверенный контур первой волны.
"use client";

import {FormEvent, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {Input} from "@/components/ui/input";
import {Label} from "@/components/ui/label";
import {FoundationSession, writeFoundationSession} from "@/lib/foundation-client";

type LoginState = {
  token?: string;
  role_code?: string;
  user?: {
    email: string;
    full_name: string;
  };
};

export function FoundationLoginForm() {
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("admin123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<LoginState | null>(null);
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setPayload(null);
    setProfile(null);

    try {
      const response = await fetch("/platform-api/api/v1/auth/login", {
        method: "POST",
        headers: {
          "content-type": "application/json"
        },
        body: JSON.stringify({email, password})
      });
      const data = (await response.json()) as LoginState | {detail?: string};
      if (!response.ok) {
        throw new Error(typeof data === "object" && data && "detail" in data ? data.detail || "login_failed" : "login_failed");
      }
      const loginState = data as LoginState;
      if (!loginState.token || !loginState.role_code) {
        throw new Error("login_payload_incomplete");
      }
      setPayload(loginState);
      writeFoundationSession(loginState as FoundationSession);

      const meResponse = await fetch("/platform-api/api/v1/auth/me", {
        headers: {
          authorization: `Bearer ${loginState.token}`
        }
      });
      const meData = (await meResponse.json()) as Record<string, unknown>;
      setProfile(meData);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "login_failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
      <Card className="glass-panel border-white/12 p-6">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="foundation-email">Email</Label>
            <Input
              id="foundation-email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="foundation-password">Password</Label>
            <Input
              id="foundation-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Вход..." : "Войти в foundation"}
          </Button>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm leading-6 text-muted-foreground">
            Demo seed: `admin@example.com / admin123`, `operator@example.com / operator123`, `customer@example.com / customer123`.
          </div>
          {error ? (
            <div className="rounded-2xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</div>
          ) : null}
        </form>
      </Card>

      <Card className="glass-panel border-white/12 p-6">
        <div className="space-y-4">
          <div>
            <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Foundation auth</div>
            <h2 className="mt-2 text-2xl leading-tight">Проверка базового login/session контура</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Экран бьёт по новому FastAPI foundation API через `/platform-api/api/v1/auth/*` и показывает, что seed, session token и role-aware профиль уже работают.
            </p>
          </div>

          {payload ? (
            <div className="space-y-3 rounded-3xl border border-white/10 bg-black/10 p-4 text-sm leading-6 text-foreground/85">
              <div>
                <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Session</div>
                <div className="mt-1 break-all font-mono text-xs">{payload.token}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Role</div>
                <div className="mt-1">{payload.role_code}</div>
              </div>
            </div>
          ) : (
            <div className="rounded-3xl border border-white/10 bg-black/10 p-4 text-sm leading-6 text-muted-foreground">
              После успешного входа здесь появится выданный token и role-aware ответ.
            </div>
          )}

          <div className="rounded-3xl border border-white/10 bg-black/10 p-4 text-sm leading-6 text-foreground/78">
            <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">/auth/me</div>
            <pre className="mt-3 overflow-x-auto whitespace-pre-wrap font-mono text-xs">
              {profile ? JSON.stringify(profile, null, 2) : "Пока пусто"}
            </pre>
          </div>
        </div>
      </Card>
    </div>
  );
}
