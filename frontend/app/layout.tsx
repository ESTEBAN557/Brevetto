import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Brevetto — Gestión Documental Inteligente",
  description:
    "Plataforma de radicación, clasificación asistida por IA y expedientes digitales para Coltebienes S.A.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
