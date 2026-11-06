"use client";

import Link from "next/link";
import { ReactNode, useEffect, useState } from "react";
import { Icon } from "./Icon";

export const MONTHS = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre",
  "Diciembre",
]; // fmt: skip

export function Crumbs({ items }: { items: { label: string; href?: string }[] }) {
  return (
    <nav className="crumbs" aria-label="Ruta de navegación">
      {items.map((item, index) => (
        <span key={index}>
          {index > 0 && " / "}
          {item.href ? <Link href={item.href}>{item.label}</Link> : <span className="cur">{item.label}</span>}
        </span>
      ))}
    </nav>
  );
}

export function PageHead({
  crumbs,
  title,
  subtitle,
  children,
}: {
  crumbs: { label: string; href?: string }[];
  title: string;
  subtitle?: string;
  children?: ReactNode;
}) {
  return (
    <>
      <Crumbs items={crumbs} />
      <div className="ph">
        <div>
          <h1>{title}</h1>
          {subtitle && <p className="sub">{subtitle}</p>}
        </div>
        {children}
      </div>
    </>
  );
}

export function SearchBox({ value, onChange, placeholder = "Buscar" }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <label className="psearch">
      <Icon name="search" size={18} />
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} aria-label={placeholder} />
    </label>
  );
}

/** Valor con retardo para no consultar la API en cada pulsación. */
export function useDebounced<T>(value: T, delay = 350): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export function PdfIcon() {
  return <span className="pdf-ico" aria-hidden="true">PDF</span>;
}

export function monthYearLabel(isoDate: string | null): string | null {
  if (!isoDate) return null;
  const [year, month] = isoDate.slice(0, 10).split("-").map(Number);
  if (!year || !month) return null;
  return `${MONTHS[month - 1].toLowerCase()} de ${year}`;
}
