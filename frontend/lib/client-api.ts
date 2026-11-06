// Cliente HTTP de Mi Portal: esquema `Authorization: Client <token>` y helpers tipados.
import { ApiError, apiFetch, buildUrl, safeJson } from "./api";
import { clearClientSession, getClientSession, saveClientSession } from "./client-auth";
import type {
  CatalogEntry,
  ClientSession,
  CodeChannel,
  DocumentCategorySlug,
  IdentificationType,
  PortalDocument,
  PortalHome,
  PortalMe,
  RequestCodeResponse,
  ServiceRequestDetail,
  ServiceRequestSummary,
} from "./client-types";
import type { DocumentType, Paginated } from "./types";

type Query = Record<string, string | number | boolean | undefined | null>;

async function clientFetch<T>(
  path: string,
  options: { method?: string; body?: BodyInit | Record<string, unknown> | null; query?: Query } = {},
): Promise<T> {
  const session = getClientSession();
  const headers = new Headers();
  let body: BodyInit | null | undefined;
  if (options.body instanceof FormData || typeof options.body === "string" || !options.body) {
    body = options.body as BodyInit | null | undefined;
  } else {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }
  if (session) headers.set("Authorization", `Client ${session.token}`);

  const response = await fetch(buildUrl(`/client-portal${path}`, options.query), {
    method: options.method ?? "GET",
    headers,
    body,
  });
  const text = await response.text();
  const data = text ? safeJson(text) : null;
  if (response.status === 401 && session) {
    clearClientSession();
    if (typeof window !== "undefined") window.location.assign("/login?expired=1");
  }
  if (!response.ok) throw new ApiError(response.status, data);
  return data as T;
}

function remember(session: ClientSession): ClientSession {
  saveClientSession({
    token: session.token,
    email: session.account.email,
    clientName: session.account.client_name,
    hasPassword: session.account.has_password,
  });
  return session;
}

export const clientAuthApi = {
  requestCode: (document_type: IdentificationType, identification_number: string, channel: CodeChannel) =>
    apiFetch<RequestCodeResponse>("/client-portal/auth/request-code/", {
      method: "POST",
      body: { document_type, identification_number, channel },
      auth: false,
    }),
  verifyCode: async (document_type: IdentificationType, identification_number: string, code: string) =>
    remember(
      await apiFetch<ClientSession>("/client-portal/auth/verify-code/", {
        method: "POST",
        body: { document_type, identification_number, code },
        auth: false,
      }),
    ),
  login: async (email: string, password: string) =>
    remember(
      await apiFetch<ClientSession>("/client-portal/auth/login/", {
        method: "POST",
        body: { email, password },
        auth: false,
      }),
    ),
  setPassword: (password: string) =>
    clientFetch<{ detail: string }>("/auth/set-password/", { method: "POST", body: { password } }),
};

async function downloadFrom(path: string): Promise<void> {
  // Igual que el portal administrativo: la URL prefirmada se abre directamente (evita CORS con el bucket).
  const { download_url } = await clientFetch<{ download_url: string }>(path);
  window.open(download_url, "_blank", "noopener");
}

export const clientApi = {
  me: () => clientFetch<PortalMe>("/me/"),
  home: (contract: string) => clientFetch<PortalHome>("/home/", { query: { contract } }),
  documents: (category: DocumentCategorySlug, query: Query = {}) =>
    clientFetch<Paginated<PortalDocument>>("/documents/", { query: { category, ...query } }),
  documentTypes: () => clientFetch<{ document_types: DocumentType[] }>("/documents/options/"),
  uploadDocument: (form: FormData) =>
    clientFetch<{
      filing_number: string;
      received_at_display: string;
      contract_number: string;
      document_type: string;
      original_filename: string;
    }>("/documents/", { method: "POST", body: form }),
  downloadDocument: (id: string) => downloadFrom(`/documents/${id}/download/`),
  catalog: () => clientFetch<CatalogEntry[]>("/request-catalog/"),
  requests: (q?: string) => clientFetch<ServiceRequestSummary[]>("/requests/", { query: { q } }),
  request: (id: string | number) => clientFetch<ServiceRequestDetail>(`/requests/${id}/`),
  createRequest: (form: FormData) =>
    clientFetch<ServiceRequestDetail>("/requests/", { method: "POST", body: form }),
  sendMessage: (id: number, body: string) =>
    clientFetch<unknown>(`/requests/${id}/messages/`, { method: "POST", body: { body } }),
  addAttachments: (id: number, files: File[]) => {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    return clientFetch<unknown>(`/requests/${id}/attachments/`, { method: "POST", body: form });
  },
  downloadAttachment: (id: number, attachmentId: number) =>
    downloadFrom(`/requests/${id}/attachments/${attachmentId}/download/`),
};
