// Manejo de la sesión JWT del portal administrativo (solo en el navegador).

const STORAGE_KEY = "brevetto.auth";

export interface AuthTokens {
  access: string;
  refresh: string;
  username: string;
}

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getTokens(): AuthTokens | null {
  if (!isBrowser()) return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthTokens;
  } catch {
    return null;
  }
}

export function saveTokens(tokens: AuthTokens): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
}

export function clearTokens(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function isAuthenticated(): boolean {
  return getTokens() !== null;
}
