// Sesión del cliente de Mi Portal (token firmado, solo en el navegador). Independiente del JWT del personal.

const STORAGE_KEY = "brevetto.client";
const CONTRACT_KEY = "brevetto.client.contract";

export interface ClientTokens {
  token: string;
  email: string;
  clientName: string;
  hasPassword: boolean;
}

const isBrowser = () => typeof window !== "undefined";

export function getClientSession(): ClientTokens | null {
  if (!isBrowser()) return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ClientTokens) : null;
  } catch {
    return null;
  }
}

export function saveClientSession(session: ClientTokens): void {
  if (isBrowser()) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearClientSession(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(STORAGE_KEY);
  window.localStorage.removeItem(CONTRACT_KEY);
}

export function getStoredContractId(): string | null {
  return isBrowser() ? window.localStorage.getItem(CONTRACT_KEY) : null;
}

export function storeContractId(id: string): void {
  if (isBrowser()) window.localStorage.setItem(CONTRACT_KEY, id);
}
