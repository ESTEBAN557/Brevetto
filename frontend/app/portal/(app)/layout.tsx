import type { ReactNode } from "react";
import { PortalShell } from "@/components/portal/PortalShell";

export default function PortalAppLayout({ children }: { children: ReactNode }) {
  return <PortalShell>{children}</PortalShell>;
}
