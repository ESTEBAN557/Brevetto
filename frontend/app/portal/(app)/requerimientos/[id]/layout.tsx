"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useCallback, useEffect, useState } from "react";
import { ErrorBox, Loading } from "@/components/DataState";
import { Icon } from "@/components/portal/Icon";
import { RequestContext } from "@/components/portal/RequestContext";
import { Crumbs } from "@/components/portal/ui";
import { clientApi } from "@/lib/client-api";
import type { ServiceRequestDetail } from "@/lib/client-types";

export default function RequestDetailLayout({ children, params }: { children: ReactNode; params: { id: string } }) {
  const pathname = usePathname();
  const [request, setRequest] = useState<ServiceRequestDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setRequest(await clientApi.request(params.id));
    } catch {
      setError("No encontramos este requerimiento.");
    }
  }, [params.id]);

  useEffect(() => {
    void reload();
  }, [reload]);

  if (error) return <ErrorBox message={error} />;
  if (!request) return <Loading />;

  const base = `/portal/requerimientos/${params.id}`;
  const tab = pathname.endsWith("/chat") ? "Chat" : pathname.endsWith("/adjuntos") ? "Adjuntos" : "Información";
  const tabs = [
    { href: base, label: "Información", icon: "info" as const, active: tab === "Información" },
    { href: `${base}/chat`, label: "Chat", icon: "chat" as const, active: tab === "Chat" },
    { href: `${base}/adjuntos`, label: "Adjuntos", icon: "clip" as const, active: tab === "Adjuntos" },
  ];

  return (
    <RequestContext.Provider value={{ request, reload }}>
      <Crumbs
        items={[
          { label: "Inicio", href: "/portal" },
          { label: "Requerimientos", href: "/portal/requerimientos" },
          { label: `#${request.id}`, href: base },
          { label: tab },
        ]}
      />
      <div className="req-title">
        <Link href="/portal/requerimientos" className="btn back-btn" aria-label="Volver a requerimientos">
          <Icon name="arrowLeft" />
        </Link>
        <h1>{request.subject}</h1>
        <span className={`rstatus ${request.status}`}>{request.status_display}</span>
      </div>
      <nav className="ptabs" aria-label="Secciones del requerimiento">
        {tabs.map((t) => (
          <Link key={t.label} href={t.href} className={t.active ? "active" : undefined}>
            <Icon name={t.icon} size={18} /> {t.label}
          </Link>
        ))}
      </nav>
      {children}
    </RequestContext.Provider>
  );
}
