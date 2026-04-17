// RU: Файл входит в проверенный контур первой волны.
"use client";

import {useSyncExternalStore} from "react";

export const FOUNDATION_SESSION_KEY = "magon.foundation.session";
const FOUNDATION_SESSION_EVENT = "magon.foundation.session.changed";
const FOUNDATION_SERVER_SESSION_SNAPSHOT: FoundationSession | null = null;

let cachedSessionRaw: string | null | undefined;
let cachedSessionSnapshot: FoundationSession | null = null;

export type FoundationSession = {
  token: string;
  role_code: string;
  user?: {
    email: string;
    full_name: string;
  };
};

function emitFoundationSessionChange(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(FOUNDATION_SESSION_EVENT));
}

export function readFoundationSession(): FoundationSession | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(FOUNDATION_SESSION_KEY);
  if (raw === cachedSessionRaw) {
    return cachedSessionSnapshot;
  }
  // RU: useSyncExternalStore требует стабильный snapshot по ссылке, поэтому повторно используем уже распарсенную session, пока raw-значение не изменилось.
  cachedSessionRaw = raw;
  if (!raw) {
    cachedSessionSnapshot = null;
    return null;
  }
  try {
    cachedSessionSnapshot = JSON.parse(raw) as FoundationSession;
    return cachedSessionSnapshot;
  } catch {
    cachedSessionSnapshot = null;
    return null;
  }
}

export function writeFoundationSession(session: FoundationSession): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(FOUNDATION_SESSION_KEY, JSON.stringify(session));
  emitFoundationSessionChange();
}

export function clearFoundationSession(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(FOUNDATION_SESSION_KEY);
  emitFoundationSessionChange();
}

function subscribeFoundationSession(callback: () => void): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }
  // RU: login/logout должны обновлять header и другие client-экраны сразу, а не только после полного reload страницы.
  const handleChange = () => callback();
  window.addEventListener("storage", handleChange);
  window.addEventListener(FOUNDATION_SESSION_EVENT, handleChange);
  return () => {
    window.removeEventListener("storage", handleChange);
    window.removeEventListener(FOUNDATION_SESSION_EVENT, handleChange);
  };
}

export function useFoundationSession(): FoundationSession | null {
  return useSyncExternalStore(subscribeFoundationSession, readFoundationSession, () => FOUNDATION_SERVER_SESSION_SNAPSHOT);
}

export function resolveFoundationLoginTarget(roleCode: string, nextPath?: string | null): string {
  if (nextPath && nextPath.startsWith("/") && !nextPath.startsWith("//")) {
    return nextPath;
  }
  if (roleCode === "operator" || roleCode === "admin") {
    return "/dashboard";
  }
  if (roleCode === "customer") {
    return "/catalog";
  }
  return "/";
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
