"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { clearTokens } from "@/lib/auth";
import { Loading } from "./DataState";

const NAV = [
  { href: "/admin", label: "Bandeja de ingesta", exact: true },
  { href: "/admin/upload", label: "Radicar documentos" },
  { href: "/admin/review", label: "Validación HITL" },
  { href: "/admin/contracts", label: "Contratos y expedientes" },
  { href: "/admin/audit", label: "Auditoría global" },
];

const TITLES: { prefix: string; title: string; sub: string }[] = [
  { prefix: "/admin/upload", title: "Radicación", sub: "Ingreso de documentos físicos y digitales" },
  { prefix: "/admin/review", title: "Validación humana", sub: "Clasificación asistida por IA con revisión del personal" },
  { prefix: "/admin/contracts", title: "Expedientes digitales", sub: "Contratos de arrendamiento y venta" },
  { prefix: "/admin/documents", title: "Documento radicado", sub: "Ficha técnica, metadatos y trazabilidad" },
  { prefix: "/admin/audit", title: "Auditoría", sub: "Bitácora inmutable de la gestión documental" },
  { prefix: "/admin", title: "Panel de control", sub: "Sistema de Gestión Documental · Coltebienes S.A." },
];

function initials(username: string | null): string {
  if (!username) return "CB";
  const parts = username.replace(/[._-]+/g, " ").trim().split(/\s+/);
  return parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("") || username.slice(0, 2).toUpperCase();
}

export function AdminShell({ children }: { children: ReactNode }) {
  const { ready, username } = useAuthGuard();
  const pathname = usePathname();
  const router = useRouter();

  if (!ready) return <Loading label="Verificando sesión…" />;

  const heading = TITLES.find((t) => pathname.startsWith(t.prefix)) ?? TITLES[TITLES.length - 1];

  function logout() {
    clearTokens();
    router.replace("/login");
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-chip">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/coltebienes-logo.png" alt="Coltebienes S.A." />
          </div>
          <div className="brand-tagline">
            <strong>Brevetto</strong>
            Gestión documental inteligente
          </div>
        </div>
        <nav>
          {NAV.map((item) => {
            const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href} className={active ? "active" : undefined}>
                <span className="dot" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <div className="session-chip">
            <span className="avatar">{initials(username)}</span>
            <span>
              <strong>{username}</strong>
              <span className="role">Personal Coltebienes · sesión JWT</span>
            </span>
          </div>
          <button type="button" className="btn-secondary btn-sm" onClick={logout}>
            Cerrar sesión
          </button>
        </div>
      </aside>
      <div className="shell-main">
        <header className="topbar no-print">
          <div>
            <div className="topbar-title">{heading.title}</div>
            <div className="topbar-sub">{heading.sub}</div>
          </div>
          <span className="live">
            <span className="dot" /> Sincronización en tiempo real
          </span>
        </header>
        {children}
      </div>
    </div>
  );
}
