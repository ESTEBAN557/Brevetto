// Tipos compartidos con la API REST de Brevetto (/api/v1).

export type ProcessingStatus =
  | "RECIBIDO"
  | "PROCESANDO"
  | "REQUIERE_REVISION"
  | "PROCESADO"
  | "FALLIDO";

export type SourceChannel =
  | "FISICO_ESCANEADO"
  | "DIGITAL_INTERNO"
  | "PORTAL_WEB"
  | "CORREO";

export type DocumentCategory =
  | "LEGAL"
  | "POLIZA"
  | "SERVICIOS"
  | "FINANCIERO"
  | "COMUNICACION";

export type ExpirationStage = "expired" | "critical" | "warning";

export interface ExpiringResponse {
  as_of: string;
  days: number;
  count: number;
  expired: number;
  expiring_soon: number;
  results: Document[];
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface DocumentType {
  id: string;
  code: string;
  name: string;
  category: DocumentCategory;
  category_label?: string;
  requires_expiration: boolean;
  description?: string;
}

export interface AiExtractedData {
  contract_number?: string | null;
  client_identification?: string | null;
  client_name?: string | null;
  document_type?: string | null;
  document_date?: string | null;
  expiration_date?: string | null;
  extracted_text_summary?: string;
  confidence_score?: number;
  error?: string;
}

export interface Document {
  id: string;
  filing_number: string;
  original_filename: string;
  file_path: string;
  file_hash: string;
  file_size_bytes: number;
  mime_type: string;
  source_channel: SourceChannel;
  processing_status: ProcessingStatus;
  needs_human_review: boolean;
  contract_id: string | null;
  contract_number: string | null;
  client_name: string | null;
  client_email: string | null;
  client_phone: string | null;
  document_type: DocumentType | null;
  ai_extracted_data: AiExtractedData;
  ai_confidence_score: number | null;
  document_date: string | null;
  expiration_date: string | null;
  days_to_expiration: number | null;
  expiration_stage: ExpirationStage | null;
  registered_by: string | null;
  external_sender_name: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentReceipt {
  id: string;
  filing_number: string;
  original_filename: string;
  file_size_bytes: number;
  source_channel: SourceChannel;
  processing_status: ProcessingStatus;
  created_at: string;
}

export interface BatchUploadResponse {
  message: string;
  items: { id: string; filing_number: string; filename: string; status: ProcessingStatus }[];
}

export interface PresignedUrl {
  filing_number: string;
  view_url: string;
  expires_in_seconds: number;
}

export interface AuditLogEntry {
  id: string;
  document: string;
  filing_number: string;
  action:
    | "CARGA"
    | "CLASIFICACION_IA"
    | "VALIDACION_HUMANA"
    | "ACTUALIZACION_METADATOS"
    | "CONSULTA_VISUAL"
    | "DESCARGA";
  action_label: string;
  performed_by: string | null;
  ip_address: string | null;
  user_agent: string;
  timestamp: string;
  details: Record<string, unknown>;
}

export interface Client {
  id: string;
  name: string;
  document_type: string;
  identification_number: string;
  email: string;
  phone: string;
  client_type: "NATURAL" | "JURIDICA";
  contracts_count: number;
  created_at: string;
}

export interface Contract {
  id: string;
  contract_number: string;
  client: string;
  client_detail: Client;
  property_address: string;
  start_date: string;
  end_date: string;
  status: "ACTIVO" | "TERMINADO" | "EN_RENOVACION";
  status_label: string;
  digital_record: { id: string; storage_path: string; documents_count: number; created_at: string } | null;
  created_at: string;
}

export interface PortalSession {
  portal_token: string;
  expires_in_seconds: number;
  contract: {
    contract_number: string;
    property_address: string;
    status: string;
    start_date: string;
    end_date: string;
  };
  client: { name: string; identification_number: string };
  document_types: DocumentType[];
  expiring_documents: {
    filing_number: string;
    document_type: string | null;
    expiration_date: string;
    expired: boolean;
  }[];
}

export interface PortalReceipt {
  filing_number: string;
  received_at: string;
  received_at_display: string;
  contract_number: string;
  client_name: string;
  document_type: string;
  original_filename: string;
  file_size_bytes: number;
  file_hash: string;
  sender_name: string;
  processing_status: ProcessingStatus;
  receipt_signature: string;
}
