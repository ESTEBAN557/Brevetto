"use client";

import { createContext, useContext } from "react";
import type { ServiceRequestDetail } from "@/lib/client-types";

export interface RequestContextValue {
  request: ServiceRequestDetail;
  reload: () => Promise<void>;
}

export const RequestContext = createContext<RequestContextValue | null>(null);

export function useServiceRequest(): RequestContextValue {
  const value = useContext(RequestContext);
  if (!value) throw new Error("useServiceRequest debe usarse dentro del detalle de requerimiento");
  return value;
}
