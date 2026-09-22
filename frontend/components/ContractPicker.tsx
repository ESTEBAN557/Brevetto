"use client";

import { useEffect, useState } from "react";
import { contractsApi } from "@/lib/api";
import type { Contract } from "@/lib/types";

interface ContractPickerProps {
  value: Contract | null;
  onChange: (contract: Contract | null) => void;
  /** Texto sugerido (p. ej. número de contrato detectado por la IA) para precargar la búsqueda. */
  initialQuery?: string | null;
  autoSelectSingleMatch?: boolean;
  placeholder?: string;
}

export function ContractPicker({
  value,
  onChange,
  initialQuery,
  autoSelectSingleMatch = false,
  placeholder = "Buscar por número de contrato, cliente o NIT…",
}: ContractPickerProps) {
  const [query, setQuery] = useState(initialQuery ?? "");
  const [results, setResults] = useState<Contract[]>([]);
  const [open, setOpen] = useState(false);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (value || query.trim().length < 2) {
      setResults([]);
      return;
    }
    const handle = window.setTimeout(async () => {
      setSearching(true);
      try {
        const data = await contractsApi.list({ search: query.trim(), status: "ACTIVO" });
        setResults(data.results);
        setOpen(true);
        if (autoSelectSingleMatch && data.results.length === 1 && initialQuery && query === initialQuery) {
          onChange(data.results[0]);
          setOpen(false);
        }
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => window.clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, value]);

  if (value) {
    return (
      <div className="picker-selected">
        <span>
          <strong>{value.contract_number}</strong> · {value.client_detail?.name}
          <span className="muted small"> · {value.property_address}</span>
        </span>
        <button type="button" className="btn-ghost btn-sm" onClick={() => onChange(null)}>
          Cambiar
        </button>
      </div>
    );
  }

  return (
    <div className="picker">
      <input
        value={query}
        placeholder={placeholder}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length && setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
      />
      {searching && <span className="muted small">Buscando…</span>}
      {open && results.length > 0 && (
        <div className="picker-results">
          {results.map((contract) => (
            <button
              key={contract.id}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onChange(contract);
                setOpen(false);
              }}
            >
              {contract.contract_number} · {contract.client_detail?.name}
              <small>
                {contract.client_detail?.identification_number} · {contract.property_address}
              </small>
            </button>
          ))}
        </div>
      )}
      {open && !searching && results.length === 0 && query.trim().length >= 2 && (
        <div className="picker-results">
          <button type="button" disabled>
            Sin contratos activos que coincidan con “{query}”.
          </button>
        </div>
      )}
    </div>
  );
}
