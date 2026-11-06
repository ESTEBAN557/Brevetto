"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ErrorBox } from "@/components/DataState";
import { Icon } from "@/components/portal/Icon";
import { ApiError } from "@/lib/api";
import { clientApi } from "@/lib/client-api";
import { formatDateTime } from "@/lib/format";
import { useServiceRequest } from "@/components/portal/RequestContext";

export default function RequestChatPage() {
  const { request, reload } = useServiceRequest();
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);
  const closed = request.status === "CERRADO";

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
  }, [request.messages.length]);

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await clientApi.sendMessage(request.id, text.trim());
      setText("");
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No fue posible enviar el mensaje.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="req-grid">
      <section className="pcard">
        <h2 className="sec-title"><Icon name="chat" size={20} /> Conversación con encargado</h2>
        <div className="chat-box">
          <div className="chat-scroll" ref={scroller}>
            {request.messages.length === 0 ? (
              <div className="chat-empty">
                <Icon name="info" size={28} />
                <p>No se han encontrado notas del caso</p>
              </div>
            ) : (
              request.messages.map((m) => (
                <div key={m.id} className={`bubble${m.author_type === "CLIENTE" ? " mine" : ""}`}>
                  <span className="meta">{m.author_type === "CLIENTE" ? "Tú" : m.author_name} · {formatDateTime(m.created_at)}</span>
                  {m.body}
                </div>
              ))
            )}
          </div>
          {closed ? (
            <div className="chat-foot closed">El requerimiento está cerrado y no permite nuevos comentarios.</div>
          ) : (
            <div className="chat-foot">
              <form className="chat-form" onSubmit={send}>
                <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Escribe un mensaje…" maxLength={3000} aria-label="Mensaje" />
                <button type="submit" disabled={busy || !text.trim()}>
                  {busy ? <span className="spinner" /> : <Icon name="arrowUpRight" size={16} />} Enviar
                </button>
              </form>
              <ErrorBox message={error} />
            </div>
          )}
        </div>
      </section>

      <section className="pcard">
        <h2 className="sec-title"><Icon name="clock" size={20} /> Seguimiento</h2>
        <ol className="track">
          {[...request.events].reverse().map((event) => (
            <li key={event.id}>
              <time>{formatDateTime(event.created_at)}</time>
              {event.note || `Estado actualizado a ${event.status_display}.`}
              {event.actor && <> <span className="muted">— {event.actor}</span></>}
              <div style={{ marginTop: "0.35rem" }}><span className={`rstatus ${event.status}`}>{event.status_display}</span></div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
