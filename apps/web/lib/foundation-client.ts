// RU: Файл входит в проверенный контур первой волны.
"use client";

export const FOUNDATION_SESSION_KEY = "magon.foundation.session";

export type FoundationSession = {
  token: string;
  role_code: string;
  user?: {
    email: string;
    full_name: string;
  };
};

export function readFoundationSession(): FoundationSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(FOUNDATION_SESSION_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as FoundationSession;
  } catch {
    return null;
  }
}

export function writeFoundationSession(session: FoundationSession): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(FOUNDATION_SESSION_KEY, JSON.stringify(session));
}

export function clearFoundationSession(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(FOUNDATION_SESSION_KEY);
}

export async function fetchFoundationJson<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const actualToken = token || readFoundationSession()?.token;
  const headers = new Headers(options.headers);
  headers.set("accept", "application/json");
  if (actualToken) {
    headers.set("authorization", `Bearer ${actualToken}`);
  }
  const response = await fetch(`/platform-api${path}`, {
    ...options,
    headers
  });
  const payload = (await response.json()) as T | {detail?: string};
  if (!response.ok) {
    throw new Error(typeof payload === "object" && payload && "detail" in payload ? payload.detail || "foundation_request_failed" : "foundation_request_failed");
  }
  return payload as T;
}

export async function downloadFoundationFile(path: string, filename: string, token?: string): Promise<void> {
  const actualToken = token || readFoundationSession()?.token;
  const headers = new Headers();
  if (actualToken) {
    headers.set("authorization", `Bearer ${actualToken}`);
  }
  const response = await fetch(`/platform-api${path}`, {headers});
  if (!response.ok) {
    let detail = "foundation_download_failed";
    try {
      const payload = (await response.json()) as {detail?: string};
      detail = payload.detail || detail;
    } catch {
      // ignore non-json failures
    }
    throw new Error(detail);
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = window.document.createElement("a");
  link.href = url;
  link.download = filename;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
