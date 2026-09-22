"use client";

import { ReactNode, useEffect, useState } from "react";
import { createPortal } from "react-dom";

interface ModalProps {
  title: ReactNode;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  size?: "narrow" | "default" | "wide";
  flush?: boolean;
}

/** Modal accesible renderizado en <body> (portal) con cierre por Escape y clic en el fondo. */
export function Modal({ title, onClose, children, footer, size = "default", flush = false }: ModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [onClose]);

  if (!mounted) return null;

  const sizeClass = size === "wide" ? " modal-wide" : size === "narrow" ? " modal-narrow" : "";

  return createPortal(
    <div className="modal-root" role="dialog" aria-modal="true">
      <div className="modal-backdrop" onClick={onClose} />
      <div className={`modal${sizeClass}`}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button type="button" className="btn-ghost btn-sm" onClick={onClose} aria-label="Cerrar">
            ✕ Cerrar
          </button>
        </div>
        <div className={`modal-body${flush ? " modal-body-flush" : ""}`}>{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}

/** Imprime únicamente el contenido del modal abierto (ver reglas @media print en globals.css). */
export function printModal(): void {
  document.body.classList.add("print-modal");
  const cleanup = () => {
    document.body.classList.remove("print-modal");
    window.removeEventListener("afterprint", cleanup);
  };
  window.addEventListener("afterprint", cleanup);
  window.print();
  window.setTimeout(cleanup, 2000);
}
