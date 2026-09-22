// Cliente HTTP hacia la API de Brevetto: JWT, refresh automático y helpers tipados.
import { clearTokens, getTokens, saveTokens } from "./auth";
import type {
  AuditLogEntry,
  BatchUploadResponse,
  Client,
  Contract,
  Document,
  DocumentReceipt,
  DocumentType,
  Paginated,
  PortalReceipt,
  PortalSession,
  PresignedUrl,
} from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(status: number, payload: unknown, message?: string) {
    super(message ?? ApiError.describe(status, payload));
    this.status = status;
    this.payload = payload;
  }

  static describe(status: number, payload: unknown): string {
    if (payload && typeof payload === "object") {
      const record = payload as Record<string, unknown>;
      if (typeof record.detail === "string") return record.detail;
      const parts = Object.entries(record).map(([field, value]) => {
        const text = Array.isArray(value) ? value.join(" ") : String(value);
        return field === "non_field_errors" ? text : `${field}: ${text}`;
      });
      if (parts.length) return parts.join(" · ");
    }
    return `Error HTTP ${status}`;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: BodyInit | Record<string, unknown> | null;
  auth?: boolean;
  query?: Record<string, string | number | boolean | undefined | null>;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(path.startsWith("http") ? path : `${API_URL}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function refreshAccessToken(): Promise<string | null> {
  const tokens = getTokens();
  if (!tokens?.refresh) return null;
  const response = await fetch(`${API_URL}/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: tokens.refresh }),
  });
  if (!response.ok) {
    clearTokens();
    return null;
  }
  const data = (await response.json()) as { access: string; refresh?: string };
  saveTokens({ ...tokens, access: data.access, refresh: data.refresh ?? tokens.refresh });
  return data.access;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, auth = true, query, headers: extraHeaders, ...rest } = options;
  const headers = new Headers(extraHeaders ?? {});
  let payload: BodyInit | null | undefined;

  if (body instanceof FormData || typeof body === "string" || body === undefined || body === null) {
    payload = body as BodyInit | null | undefined;
  } else {
    headers.set("Content-Type", "application/json");
    payload = JSON.stringify(body);
  }

  const doRequest = async (access?: string | null) => {
    if (auth && access) headers.set("Authorization", `Bearer ${access}`);
    return fetch(buildUrl(path, query), { ...rest, headers, body: payload });
  };

  let response = await doRequest(auth ? getTokens()?.access : null);
  if (auth && response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      response = await doRequest(refreshed);
    } else if (typeof window !== "undefined") {
      window.location.assign("/login");
    }
  }

  const text = await response.text();
  const data = text ? safeJson(text) : null;
  if (!response.ok) throw new ApiError(response.status, data);
  return data as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

// ------------------------------------------------------------------ auth ---
export async function login(username: string, password: string) {
  const data = await apiFetch<{ access: string; refresh: string }>("/auth/token/", {
    method: "POST",
    body: { username, password },
    auth: false,
  });
  saveTokens({ ...data, username });
  return data;
}

// ------------------------------------------------------------- documentos ---
export const documentsApi = {
  list: (query?: RequestOptions["query"]) => apiFetch<Paginated<Document>>("/documents/", { query }),
  get: (id: string) => apiFetch<Document>(`/documents/${id}/`),
  pendingReview: (query?: RequestOptions["query"]) =>
    apiFetch<Paginated<Document>>("/documents/pending-review/", { query }),
  upload: (form: FormData) => apiFetch<DocumentReceipt>("/documents/upload/", { method: "POST", body: form }),
  batchUpload: (form: FormData) =>
    apiFetch<BatchUploadResponse>("/documents/batch-upload/", { method: "POST", body: form }),
  validate: (id: string, body: { contract_id: string; document_type_id: string; expiration_date?: string | null; document_date?: string | null }) =>
    apiFetch<Document>(`/documents/${id}/validate/`, { method: "POST", body }),
  updateMetadata: (id: string, body: Record<string, unknown>) =>
    apiFetch<Document>(`/documents/${id}/metadata/`, { method: "PATCH", body }),
  viewUrl: (id: string) => apiFetch<PresignedUrl>(`/documents/${id}/view-url/`),
  downloadUrl: (id: string) =>
    apiFetch<{ download_url: string; original_filename: string }>(`/documents/${id}/download-url/`),
  auditTrail: (id: string) => apiFetch<Paginated<AuditLogEntry>>(`/documents/${id}/audit-trail/`),
};

// -------------------------------------------------------------- contratos ---
export const contractsApi = {
  list: (query?: RequestOptions["query"]) => apiFetch<Paginated<Contract>>("/contracts/", { query }),
  get: (id: string) => apiFetch<Contract>(`/contracts/${id}/`),
  create: (body: Record<string, unknown>) => apiFetch<Contract>("/contracts/", { method: "POST", body }),
  documents: (id: string, query?: RequestOptions["query"]) =>
    apiFetch<Paginated<Document>>(`/contracts/${id}/documents/`, { query }),
  auditTrail: (id: string) => apiFetch<Paginated<AuditLogEntry>>(`/contracts/${id}/audit-trail/`),
};

export const clientsApi = {
  list: (query?: RequestOptions["query"]) => apiFetch<Paginated<Client>>("/clients/", { query }),
  create: (body: Record<string, unknown>) => apiFetch<Client>("/clients/", { method: "POST", body }),
};

export const documentTypesApi = {
  list: () => apiFetch<DocumentType[]>("/document-types/"),
};

// ----------------------------------------------------------------- portal ---
export const portalApi = {
  verify: (contract_number: string, identification_number: string) =>
    apiFetch<PortalSession>("/portal/verify-contract/", {
      method: "POST",
      body: { contract_number, identification_number },
      auth: false,
    }),
  submit: (token: string, form: FormData) =>
    apiFetch<PortalReceipt>("/portal/submit-document/", {
      method: "POST",
      body: form,
      auth: false,
      headers: { "X-Portal-Token": token },
    }),
};
