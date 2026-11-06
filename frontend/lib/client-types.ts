// Tipos de la API de Mi Portal (/client-portal/).

export type IdentificationType = "NIT" | "CC" | "CE" | "PASAPORTE";
export type CodeChannel = "sms" | "email";

export interface ClientSession {
  token: string;
  expires_in_seconds: number;
  account: { email: string; client_name: string; has_password: boolean };
}

export interface RequestCodeResponse {
  detail: string;
  destination?: string;
  channel?: CodeChannel;
  /** Solo en desarrollo (CLIENT_OTP_DEV_ECHO): no hay proveedor SMS integrado. */
  dev_code?: string;
}

export interface PortalContract {
  id: string;
  contract_number: string;
  property_address: string;
  status: string;
  start_date: string;
  end_date: string;
}

export interface PortalNotification {
  document_type: string;
  contract_number: string;
  expiration_date: string;
  expired: boolean;
}

export interface PortalMe {
  client: { name: string; document_type: string; identification_number: string; email: string };
  has_password: boolean;
  contracts: PortalContract[];
  executive: { name: string; email: string; whatsapp: string };
  notifications: PortalNotification[];
}

export type DocumentCategorySlug = "estados-de-cuenta" | "certificados" | "facturas" | "contratos";

export interface PortalHome {
  contract: PortalContract;
  days_remaining: number;
  document_counts: Record<DocumentCategorySlug, number>;
  total_documents: number;
  open_requests: number;
}

export interface PortalDocument {
  id: string;
  filing_number: string;
  title: string;
  document_type_name: string | null;
  document_type_code: string | null;
  contract_number: string | null;
  property_address: string | null;
  document_date: string | null;
  expiration_date: string | null;
  created_at: string;
  original_filename: string;
  file_size_bytes: number;
  detail: {
    beneficiary: { name: string; identification_type: string; identification_number: string; email: string };
    transaction: { filing_number: string; document_date: string | null; registered_at: string; channel: string };
  };
}

export interface CatalogEntry {
  id: number;
  case_type: string;
  service: string;
  subcategory: string;
}

export type RequestStatus = "NUEVO" | "ASIGNADO" | "EN_PROCESO" | "RESUELTO" | "CERRADO";

export interface ServiceRequestSummary {
  id: number;
  subject: string;
  created_at: string;
  service: string;
  subcategory: string;
  assigned_to: string;
  status: RequestStatus;
  status_display: string;
  contract_number: string;
}

export interface ServiceRequestDetail extends ServiceRequestSummary {
  case_type: string;
  description: string;
  solution: string;
  updated_at: string;
  property_address: string;
  reported_by: string;
  events: { id: number; status: RequestStatus; status_display: string; actor: string; note: string; created_at: string }[];
  messages: { id: number; author_type: "CLIENTE" | "PERSONAL"; author_name: string; body: string; created_at: string }[];
  attachments: {
    id: number;
    from_client: boolean;
    original_filename: string;
    file_size_bytes: number;
    mime_type: string;
    created_at: string;
  }[];
}
