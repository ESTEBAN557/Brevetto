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
];

export function AdminShell({ children }: { children: ReactNode }) {
  const { ready, username } = useAuthGuard();
  const pathname = usePathname();
  const router = useRouter();

  if (!ready) return <Loading label="Verificando sesión…" />;

  function logout() {
    clearTokens();
    router.replace("/login");
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          Brevetto
          <small>Coltebienes S.A. · Gestión documental</small>
        </div>
        <nav>
          {NAV.map((item) => {
            const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href} className={active ? "active" : undefined}>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          Sesión: <strong>{username}</strong>
          <button type="button" className="btn-secondary btn-sm" onClick={logout}>
            Cerrar sesión
          </button>
        </div>
      </aside>
      <div className="shell-main">{children}</div>
    </div>
  );
}
