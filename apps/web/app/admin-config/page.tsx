"use client";

import Link from "next/link";
import {FormEvent, useCallback, useEffect, useMemo, useState} from "react";

import {Button} from "@/components/ui/button";
import {Card} from "@/components/ui/card";
import {Field, FieldHint, FieldLabel} from "@/components/ui/field";
import {Input} from "@/components/ui/input";
import {Textarea} from "@/components/ui/textarea";
import {fetchFoundationJson, readFoundationSession} from "@/lib/foundation-client";

type ReasonCodeItem = {
  code: string;
  title: string;
  category: string;
  severity: string;
  default_visibility_scope: string;
  description?: string | null;
  metadata_json?: Record<string, unknown>;
  is_active: boolean;
};

type RuleItem = {
  id: string;
  code: string;
  name: string;
  scope: string;
  rule_kind: string;
  latest_version_no: number;
  enabled: boolean;
  description?: string | null;
  config_json?: Record<string, unknown>;
  metadata_json?: Record<string, unknown>;
};

type NotificationRuleItem = {
  code: string;
  event_type: string;
  entity_type: string;
  recipient_scope: string;
  channel: string;
  template_key: string;
  min_interval_seconds: number;
  enabled: boolean;
  rule_code?: string | null;
  metadata_json?: Record<string, unknown>;
};

type SupplierSourceItem = {
  code: string;
  label: string;
  adapter_key: string;
  enabled: boolean;
  config_json: Record<string, unknown>;
  schedule: {
    enabled: boolean;
    interval_minutes: number;
  };
  classification: {
    mode: string;
    llm_enabled: boolean;
  };
};

function parseOptionalJson(raw: FormDataEntryValue | null): Record<string, unknown> | undefined {
  if (typeof raw !== "string") return undefined;
  const trimmed = raw.trim();
  if (!trimmed) return undefined;
  return JSON.parse(trimmed) as Record<string, unknown>;
}

async function requestFoundation<T>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  return fetchFoundationJson<T>(path, options, token);
}

function SessionGate({children}: {children: React.ReactNode}) {
  // RU: Admin-config нельзя отдавать вне admin-сессии, иначе базовые workflow-настройки утекут в публичный или customer-контур.
  const session = readFoundationSession();
  if (!session?.token || session.role_code !== "admin") {
    return (
      <main className="container space-y-6 py-10">
        <Card className="glass-panel border-white/12 p-6">
          <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Админ-настройки</div>
          <h1 className="mt-2 text-3xl leading-tight">Настройка платформы</h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground">
            Для этого экрана нужен действующий админский токен. Здесь настраиваются сущности и правила wave1, а не сиды в коде.
          </p>
          <div className="mt-5 flex gap-3">
            <Link href="/login"><Button>Вход</Button></Link>
            <Link href="/admin-dashboard"><Button variant="secondary">Админ-панель</Button></Link>
          </div>
        </Card>
      </main>
    );
  }
  return <>{children}</>;
}

export default function AdminConfigPage() {
  const session = readFoundationSession();
  const token = session?.token ?? "";
  const [reasonCodes, setReasonCodes] = useState<ReasonCodeItem[]>([]);
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [notificationRules, setNotificationRules] = useState<NotificationRuleItem[]>([]);
  const [supplierSources, setSupplierSources] = useState<SupplierSourceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const ruleOptions = useMemo(() => rules.map((item) => item.code), [rules]);

  const loadAll = useCallback(async () => {
    // RU: Экран грузит только active foundation endpoints, чтобы бизнес-настройка не жила в сидах или скрытых fallback-ручках.
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [reasonPayload, rulePayload, notificationPayload, sourcePayload] = await Promise.all([
        requestFoundation<{items: ReasonCodeItem[]}>("/api/v1/operator/reason-codes", token),
        requestFoundation<{items: RuleItem[]}>("/api/v1/operator/rules", token),
        requestFoundation<{items: NotificationRuleItem[]}>("/api/v1/admin/notification-rules", token),
        requestFoundation<{items: SupplierSourceItem[]}>("/api/v1/operator/supplier-sources", token),
      ]);
      setReasonCodes(reasonPayload.items);
      setRules(rulePayload.items);
      setNotificationRules(notificationPayload.items);
      setSupplierSources(sourcePayload.items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "admin_config_load_failed");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  async function submitAction(handler: () => Promise<void>, successMessage: string) {
    setStatus(null);
    setError(null);
    try {
      await handler();
      setStatus(successMessage);
      await loadAll();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "admin_config_action_failed");
    }
  }

  return (
    <SessionGate>
      <main className="container space-y-6 py-10">
        <Card className="glass-panel border-white/12 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Системная настройка</div>
              <h1 className="mt-2 text-3xl leading-tight">Настройка сущностей и правил</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-muted-foreground">
                Этот экран убирает зависимость от сидов и правок кода для базовой конфигурации wave1: reason codes, rules, notification rules и supplier source settings.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href="/admin-dashboard"><Button variant="secondary">Админ-панель</Button></Link>
              <Link href="/suppliers"><Button variant="secondary">Поставщики</Button></Link>
              <Link href="/request-workbench"><Button variant="secondary">Заявки</Button></Link>
            </div>
          </div>
        </Card>

        {loading ? <Card className="glass-panel border-white/12 p-6">Загрузка конфигурации...</Card> : null}
        {error ? <Card className="border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100">{error}</Card> : null}
        {status ? <Card className="border-emerald-400/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">{status}</Card> : null}

        <section className="grid gap-6 xl:grid-cols-2">
          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Reason codes</h2>
            <p className="mt-2 text-sm text-muted-foreground">Коды причин и blocker semantics, которые видит workflow и UI.</p>
            <form
              className="mt-4 grid gap-3 rounded-2xl border border-white/10 bg-black/10 p-4"
              onSubmit={(event: FormEvent<HTMLFormElement>) => {
                event.preventDefault();
                const formData = new FormData(event.currentTarget);
                void submitAction(async () => {
                  await requestFoundation("/api/v1/admin/reason-codes", token, {
                    method: "POST",
                    headers: {"content-type": "application/json"},
                    body: JSON.stringify({
                      code: String(formData.get("code") || ""),
                      title: String(formData.get("title") || ""),
                      category: String(formData.get("category") || ""),
                      severity: String(formData.get("severity") || "info"),
                      default_visibility_scope: String(formData.get("default_visibility_scope") || "internal"),
                      description: String(formData.get("description") || "") || null,
                      is_active: formData.get("is_active") === "on",
                      metadata_json: parseOptionalJson(formData.get("metadata_json")),
                    }),
                  });
                  event.currentTarget.reset();
                }, "Reason code создан.");
              }}
            >
              <div className="grid gap-3 md:grid-cols-2">
                <Field><FieldLabel>Code</FieldLabel><Input name="code" placeholder="customer_artwork_missing" required /></Field>
                <Field><FieldLabel>Заголовок</FieldLabel><Input name="title" placeholder="Отсутствует artwork" required /></Field>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <Field><FieldLabel>Категория</FieldLabel><Input name="category" placeholder="request" required /></Field>
                <Field>
                  <FieldLabel>Severity</FieldLabel>
                  <select name="severity" className="h-11 rounded-lg border border-input bg-background px-4 text-sm">
                    <option value="info">info</option>
                    <option value="warning">warning</option>
                    <option value="critical">critical</option>
                  </select>
                </Field>
                <Field>
                  <FieldLabel>Visibility</FieldLabel>
                  <select name="default_visibility_scope" className="h-11 rounded-lg border border-input bg-background px-4 text-sm">
                    <option value="internal">internal</option>
                    <option value="customer">customer</option>
                    <option value="supplier">supplier</option>
                  </select>
                </Field>
              </div>
              <Field><FieldLabel>Описание</FieldLabel><Textarea name="description" placeholder="Короткое объяснение для UI и аудита." /></Field>
              <Field><FieldLabel>Metadata JSON</FieldLabel><Textarea name="metadata_json" placeholder='{"owner":"ops"}' /></Field>
              <label className="flex items-center gap-2 text-sm font-medium"><input type="checkbox" name="is_active" defaultChecked /> Активен</label>
              <Button type="submit">Создать reason code</Button>
            </form>
            <div className="mt-4 space-y-3">
              {reasonCodes.map((item) => (
                <form
                  key={item.code}
                  className="rounded-2xl border border-white/10 bg-black/10 p-4"
                  onSubmit={(event: FormEvent<HTMLFormElement>) => {
                    event.preventDefault();
                    const formData = new FormData(event.currentTarget);
                    void submitAction(async () => {
                      await requestFoundation(`/api/v1/admin/reason-codes/${item.code}`, token, {
                        method: "PATCH",
                        headers: {"content-type": "application/json"},
                        body: JSON.stringify({
                          title: String(formData.get("title") || ""),
                          category: String(formData.get("category") || ""),
                          severity: String(formData.get("severity") || "info"),
                          default_visibility_scope: String(formData.get("default_visibility_scope") || "internal"),
                          description: String(formData.get("description") || "") || null,
                          is_active: formData.get("is_active") === "on",
                          metadata_json: parseOptionalJson(formData.get("metadata_json")) ?? {},
                        }),
                      });
                    }, `Reason code ${item.code} обновлён.`);
                  }}
                >
                  <div className="mb-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.code}</div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <Field><FieldLabel>Заголовок</FieldLabel><Input name="title" defaultValue={item.title} required /></Field>
                    <Field><FieldLabel>Категория</FieldLabel><Input name="category" defaultValue={item.category} required /></Field>
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-3">
                    <Field>
                      <FieldLabel>Severity</FieldLabel>
                      <select name="severity" defaultValue={item.severity} className="h-11 rounded-lg border border-input bg-background px-4 text-sm">
                        <option value="info">info</option>
                        <option value="warning">warning</option>
                        <option value="critical">critical</option>
                      </select>
                    </Field>
                    <Field>
                      <FieldLabel>Visibility</FieldLabel>
                      <select name="default_visibility_scope" defaultValue={item.default_visibility_scope} className="h-11 rounded-lg border border-input bg-background px-4 text-sm">
                        <option value="internal">internal</option>
                        <option value="customer">customer</option>
                        <option value="supplier">supplier</option>
                      </select>
                    </Field>
                    <label className="mt-7 flex items-center gap-2 text-sm font-medium"><input type="checkbox" name="is_active" defaultChecked={item.is_active} /> Активен</label>
                  </div>
                  <Field className="mt-3"><FieldLabel>Описание</FieldLabel><Textarea name="description" defaultValue={item.description ?? ""} /></Field>
                  <Field className="mt-3"><FieldLabel>Metadata JSON</FieldLabel><Textarea name="metadata_json" defaultValue={JSON.stringify(item.metadata_json ?? {}, null, 2)} /></Field>
                  <div className="mt-3 flex justify-end"><Button type="submit" variant="secondary">Сохранить</Button></div>
                </form>
              ))}
            </div>
          </Card>

          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Rules и версии</h2>
            <p className="mt-2 text-sm text-muted-foreground">Transition guards и explainable rule versions для критичных переходов.</p>
            <form
              className="mt-4 grid gap-3 rounded-2xl border border-white/10 bg-black/10 p-4"
              onSubmit={(event: FormEvent<HTMLFormElement>) => {
                event.preventDefault();
                const formData = new FormData(event.currentTarget);
                void submitAction(async () => {
                  await requestFoundation("/api/v1/admin/rules", token, {
                    method: "POST",
                    headers: {"content-type": "application/json"},
                    body: JSON.stringify({
                      name: String(formData.get("name") || ""),
                      scope: String(formData.get("scope") || ""),
                      rule_kind: String(formData.get("rule_kind") || "transition_guard"),
                      description: String(formData.get("description") || "") || null,
                      enabled: formData.get("enabled") === "on",
                      config_json: parseOptionalJson(formData.get("config_json")),
                      metadata_json: parseOptionalJson(formData.get("metadata_json")),
                      explainability_json: parseOptionalJson(formData.get("explainability_json")),
                    }),
                  });
                  event.currentTarget.reset();
                }, "Правило создано.");
              }}
            >
              <div className="grid gap-3 md:grid-cols-2">
                <Field><FieldLabel>Название</FieldLabel><Input name="name" placeholder="Guard: order start requires payment" required /></Field>
                <Field><FieldLabel>Scope</FieldLabel><Input name="scope" placeholder="order_transition" required /></Field>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Field><FieldLabel>Rule kind</FieldLabel><Input name="rule_kind" defaultValue="transition_guard" required /></Field>
                <label className="mt-7 flex items-center gap-2 text-sm font-medium"><input type="checkbox" name="enabled" defaultChecked /> Включено</label>
              </div>
              <Field><FieldLabel>Описание</FieldLabel><Textarea name="description" placeholder="Что именно блокирует или разрешает правило." /></Field>
              <Field><FieldLabel>Config JSON</FieldLabel><Textarea name="config_json" placeholder='{"required_reason_codes":["payment_confirmed"]}' /></Field>
              <Field><FieldLabel>Metadata JSON</FieldLabel><Textarea name="metadata_json" placeholder='{"owner":"admin"}' /></Field>
              <Field><FieldLabel>Explainability JSON</FieldLabel><Textarea name="explainability_json" placeholder='{"summary":"Start only after payment confirmation."}' /></Field>
              <Button type="submit">Создать правило</Button>
            </form>
            <div className="mt-4 space-y-3">
              {rules.map((item) => (
                <div key={item.code} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                  <form
                    onSubmit={(event: FormEvent<HTMLFormElement>) => {
                      event.preventDefault();
                      const formData = new FormData(event.currentTarget);
                      void submitAction(async () => {
                        await requestFoundation(`/api/v1/admin/rules/${item.code}`, token, {
                          method: "PATCH",
                          headers: {"content-type": "application/json"},
                          body: JSON.stringify({
                            name: String(formData.get("name") || ""),
                            scope: String(formData.get("scope") || ""),
                            rule_kind: String(formData.get("rule_kind") || ""),
                            description: String(formData.get("description") || "") || null,
                            enabled: formData.get("enabled") === "on",
                            config_json: parseOptionalJson(formData.get("config_json")) ?? {},
                            metadata_json: parseOptionalJson(formData.get("metadata_json")) ?? {},
                          }),
                        });
                      }, `Правило ${item.code} обновлено.`);
                    }}
                  >
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <div>
                        <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.code}</div>
                        <div className="mt-1 text-sm text-muted-foreground">Версия {item.latest_version_no}</div>
                      </div>
                      <label className="flex items-center gap-2 text-sm font-medium"><input type="checkbox" name="enabled" defaultChecked={item.enabled} /> Включено</label>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2">
                      <Field><FieldLabel>Название</FieldLabel><Input name="name" defaultValue={item.name} required /></Field>
                      <Field><FieldLabel>Scope</FieldLabel><Input name="scope" defaultValue={item.scope} required /></Field>
                    </div>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <Field><FieldLabel>Rule kind</FieldLabel><Input name="rule_kind" defaultValue={item.rule_kind} required /></Field>
                      <Field><FieldLabel>Описание</FieldLabel><Input name="description" defaultValue={item.description ?? ""} /></Field>
                    </div>
                    <Field className="mt-3"><FieldLabel>Config JSON</FieldLabel><Textarea name="config_json" defaultValue={JSON.stringify(item.config_json ?? {}, null, 2)} /></Field>
                    <Field className="mt-3"><FieldLabel>Metadata JSON</FieldLabel><Textarea name="metadata_json" defaultValue={JSON.stringify(item.metadata_json ?? {}, null, 2)} /></Field>
                    <div className="mt-3 flex flex-wrap justify-end gap-2">
                      <Button type="submit" variant="secondary">Сохранить правило</Button>
                      <Button
                        type="button"
                        onClick={() =>
                          void submitAction(async () => {
                            await requestFoundation(`/api/v1/admin/rules/${item.code}/versions`, token, {
                              method: "POST",
                              headers: {"content-type": "application/json"},
                              body: JSON.stringify({
                                version_status: "active",
                                metadata_json: item.metadata_json ?? {},
                                explainability_json: {summary: item.description || item.name},
                              }),
                            });
                          }, `Создана новая версия для ${item.code}.`)
                        }
                      >
                        Выпустить новую версию
                      </Button>
                    </div>
                  </form>
                </div>
              ))}
            </div>
          </Card>
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Notification rules</h2>
            <p className="mt-2 text-sm text-muted-foreground">Шаблоны уведомлений и антиспам-интервалы для role-scoped inbox.</p>
            <form
              className="mt-4 grid gap-3 rounded-2xl border border-white/10 bg-black/10 p-4"
              onSubmit={(event: FormEvent<HTMLFormElement>) => {
                event.preventDefault();
                const formData = new FormData(event.currentTarget);
                void submitAction(async () => {
                  await requestFoundation("/api/v1/admin/notification-rules", token, {
                    method: "POST",
                    headers: {"content-type": "application/json"},
                    body: JSON.stringify({
                      event_type: String(formData.get("event_type") || ""),
                      entity_type: String(formData.get("entity_type") || ""),
                      recipient_scope: String(formData.get("recipient_scope") || "internal"),
                      channel: String(formData.get("channel") || "inbox"),
                      template_key: String(formData.get("template_key") || ""),
                      min_interval_seconds: Number(formData.get("min_interval_seconds") || 0),
                      enabled: formData.get("enabled") === "on",
                      rule_code: String(formData.get("rule_code") || "") || null,
                      metadata_json: parseOptionalJson(formData.get("metadata_json")),
                    }),
                  });
                  event.currentTarget.reset();
                }, "Notification rule создан.");
              }}
            >
              <div className="grid gap-3 md:grid-cols-2">
                <Field><FieldLabel>Event type</FieldLabel><Input name="event_type" placeholder="request_status_changed" required /></Field>
                <Field><FieldLabel>Entity type</FieldLabel><Input name="entity_type" placeholder="request" required /></Field>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <Field><FieldLabel>Recipient scope</FieldLabel><Input name="recipient_scope" defaultValue="internal" required /></Field>
                <Field><FieldLabel>Channel</FieldLabel><Input name="channel" defaultValue="inbox" required /></Field>
                <Field><FieldLabel>Template key</FieldLabel><Input name="template_key" placeholder="request_blocker_internal" required /></Field>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <Field><FieldLabel>Мин. интервал, сек</FieldLabel><Input name="min_interval_seconds" type="number" defaultValue={0} min={0} /></Field>
                <Field>
                  <FieldLabel>Связанное правило</FieldLabel>
                  <select name="rule_code" className="h-11 rounded-lg border border-input bg-background px-4 text-sm" defaultValue="">
                    <option value="">без связанного правила</option>
                    {ruleOptions.map((ruleCode) => <option key={ruleCode} value={ruleCode}>{ruleCode}</option>)}
                  </select>
                </Field>
                <label className="mt-7 flex items-center gap-2 text-sm font-medium"><input type="checkbox" name="enabled" defaultChecked /> Включено</label>
              </div>
              <Field><FieldLabel>Metadata JSON</FieldLabel><Textarea name="metadata_json" placeholder='{"title":"Нужно уточнение"}' /></Field>
              <Button type="submit">Создать notification rule</Button>
            </form>
            <div className="mt-4 space-y-3">
              {notificationRules.map((item) => (
                <form
                  key={item.code}
                  className="rounded-2xl border border-white/10 bg-black/10 p-4"
                  onSubmit={(event: FormEvent<HTMLFormElement>) => {
                    event.preventDefault();
                    const formData = new FormData(event.currentTarget);
                    void submitAction(async () => {
                      await requestFoundation(`/api/v1/admin/notification-rules/${item.code}`, token, {
                        method: "PATCH",
                        headers: {"content-type": "application/json"},
                        body: JSON.stringify({
                          event_type: String(formData.get("event_type") || ""),
                          entity_type: String(formData.get("entity_type") || ""),
                          recipient_scope: String(formData.get("recipient_scope") || ""),
                          channel: String(formData.get("channel") || ""),
                          template_key: String(formData.get("template_key") || ""),
                          min_interval_seconds: Number(formData.get("min_interval_seconds") || 0),
                          enabled: formData.get("enabled") === "on",
                          rule_code: String(formData.get("rule_code") || ""),
                          metadata_json: parseOptionalJson(formData.get("metadata_json")) ?? {},
                        }),
                      });
                    }, `Notification rule ${item.code} обновлён.`);
                  }}
                >
                  <div className="mb-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.code}</div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <Field><FieldLabel>Event type</FieldLabel><Input name="event_type" defaultValue={item.event_type} required /></Field>
                    <Field><FieldLabel>Entity type</FieldLabel><Input name="entity_type" defaultValue={item.entity_type} required /></Field>
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-3">
                    <Field><FieldLabel>Recipient scope</FieldLabel><Input name="recipient_scope" defaultValue={item.recipient_scope} required /></Field>
                    <Field><FieldLabel>Channel</FieldLabel><Input name="channel" defaultValue={item.channel} required /></Field>
                    <Field><FieldLabel>Template key</FieldLabel><Input name="template_key" defaultValue={item.template_key} required /></Field>
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-3">
                    <Field><FieldLabel>Мин. интервал, сек</FieldLabel><Input name="min_interval_seconds" type="number" min={0} defaultValue={item.min_interval_seconds} /></Field>
                    <Field>
                      <FieldLabel>Связанное правило</FieldLabel>
                      <select name="rule_code" className="h-11 rounded-lg border border-input bg-background px-4 text-sm" defaultValue={item.rule_code ?? ""}>
                        <option value="">без связанного правила</option>
                        {ruleOptions.map((ruleCode) => <option key={ruleCode} value={ruleCode}>{ruleCode}</option>)}
                      </select>
                    </Field>
                    <label className="mt-7 flex items-center gap-2 text-sm font-medium"><input type="checkbox" name="enabled" defaultChecked={item.enabled} /> Включено</label>
                  </div>
                  <Field className="mt-3"><FieldLabel>Metadata JSON</FieldLabel><Textarea name="metadata_json" defaultValue={JSON.stringify(item.metadata_json ?? {}, null, 2)} /></Field>
                  <div className="mt-3 flex justify-end"><Button type="submit" variant="secondary">Сохранить</Button></div>
                </form>
              ))}
            </div>
          </Card>

          <Card className="glass-panel border-white/12 p-5">
            <h2 className="text-xl">Supplier source settings</h2>
            <p className="mt-2 text-sm text-muted-foreground">Настройка periodic parsing/classification без редактирования bootstrap или сидов.</p>
            <div className="mt-4 space-y-3">
              {supplierSources.map((item) => (
                <form
                  key={item.code}
                  className="rounded-2xl border border-white/10 bg-black/10 p-4"
                  onSubmit={(event: FormEvent<HTMLFormElement>) => {
                    event.preventDefault();
                    const formData = new FormData(event.currentTarget);
                    void submitAction(async () => {
                      await requestFoundation(`/api/v1/admin/supplier-sources/${item.code}`, token, {
                        method: "PATCH",
                        headers: {"content-type": "application/json"},
                        body: JSON.stringify({
                          label: String(formData.get("label") || ""),
                          enabled: formData.get("enabled") === "on",
                          schedule_enabled: formData.get("schedule_enabled") === "on",
                          schedule_interval_minutes: Number(formData.get("schedule_interval_minutes") || 60),
                          classification_mode: String(formData.get("classification_mode") || "deterministic_only"),
                          config_json: parseOptionalJson(formData.get("config_json")) ?? item.config_json,
                        }),
                      });
                    }, `Источник ${item.code} обновлён.`);
                  }}
                >
                  <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.code}</div>
                      <div className="mt-1 text-sm text-muted-foreground">{item.adapter_key}</div>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      LLM fallback: {item.classification.llm_enabled ? "включён" : "выключен"}
                    </div>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <Field><FieldLabel>Название</FieldLabel><Input name="label" defaultValue={item.label} required /></Field>
                    <Field><FieldLabel>Классификация</FieldLabel>
                      <select name="classification_mode" defaultValue={item.classification.mode} className="h-11 rounded-lg border border-input bg-background px-4 text-sm">
                        <option value="deterministic_only">deterministic_only</option>
                        <option value="ai_assisted_fallback">ai_assisted_fallback</option>
                      </select>
                    </Field>
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-3">
                    <label className="mt-7 flex items-center gap-2 text-sm font-medium"><input type="checkbox" name="enabled" defaultChecked={item.enabled} /> Источник включён</label>
                    <label className="mt-7 flex items-center gap-2 text-sm font-medium"><input type="checkbox" name="schedule_enabled" defaultChecked={item.schedule.enabled} /> Periodic запуск</label>
                    <Field><FieldLabel>Интервал, мин</FieldLabel><Input name="schedule_interval_minutes" type="number" min={5} defaultValue={item.schedule.interval_minutes} /></Field>
                  </div>
                  <Field className="mt-3">
                    <FieldLabel>Config JSON</FieldLabel>
                    <Textarea name="config_json" defaultValue={JSON.stringify(item.config_json ?? {}, null, 2)} />
                    <FieldHint>Здесь же можно явно задать parser/query/source-specific параметры.</FieldHint>
                  </Field>
                  <div className="mt-3 flex justify-end"><Button type="submit" variant="secondary">Сохранить источник</Button></div>
                </form>
              ))}
            </div>
          </Card>
        </section>
      </main>
    </SessionGate>
  );
}
