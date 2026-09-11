import { useMemo, useState } from "react";
import { AlertCircle, ArrowDownLeft, ArrowUpRight, Bell, ScrollText, X } from "lucide-react";

const META = {
  request: { label: "Solicitud", Icon: ArrowUpRight, cls: "req" },
  response: { label: "Respuesta", Icon: ArrowDownLeft, cls: "res" },
  notification: { label: "Notificación", Icon: Bell, cls: "not" },
  error: { label: "Error", Icon: AlertCircle, cls: "err" },
};

// "tools/call" solo dice poco; se agrega el nombre de la herramienta.
function describe(msg) {
  if (msg.method === "tools/call") return `tools/call · ${msg.params?.name ?? "?"}`;
  return msg.method ?? "";
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString("es-GT", { hour12: false });
}

export default function LogPanel({ entries, onClose }) {
  const [filter, setFilter] = useState("all");

  const servers = useMemo(() => [...new Set(entries.map((e) => e.server))], [entries]);

  // Las respuestas JSON-RPC no traen el método, solo el id: se recupera
  // buscando la solicitud que tenía ese mismo id en ese mismo servidor.
  const methodById = useMemo(() => {
    const map = {};
    for (const e of entries) {
      if (e.direction === "request") map[`${e.server}:${e.message.id}`] = describe(e.message);
    }
    return map;
  }, [entries]);

  // Lo más reciente arriba, para ver el tráfico en vivo sin hacer scroll.
  const shown = useMemo(
    () => entries.filter((e) => filter === "all" || e.server === filter).slice().reverse(),
    [entries, filter]
  );

  return (
    <aside className="card log-panel" aria-label="Registro de mensajes MCP">
      <div className="log-header">
        <h2 className="section-title">
          <span className="icon-wrap blue"><ScrollText size={16} /></span>
          Registro MCP
        </h2>
        <button className="icon-btn small" onClick={onClose} aria-label="Cerrar registro">
          <X size={18} />
        </button>
      </div>

      <div className="log-filters" role="group" aria-label="Filtrar por servidor">
        {["all", ...servers].map((s) => (
          <button
            key={s}
            className={`filter ${filter === s ? "active" : ""}`}
            onClick={() => setFilter(s)}
          >
            {s === "all" ? "Todos" : s}
          </button>
        ))}
      </div>

      <div className="log-list">
        {shown.length === 0 && <p className="muted">Aún no hay mensajes MCP.</p>}

        {shown.map((e) => {
          const meta = META[e.direction] ?? META.request;
          const isReply = e.direction === "response" || e.direction === "error";
          const title = isReply
            ? methodById[`${e.server}:${e.message.id}`] ?? `id ${e.message.id}`
            : describe(e.message);

          return (
            <details key={e.index} className={`log-entry ${meta.cls}`}>
              <summary>
                <span className="log-head">
                  <span className={`dir ${meta.cls}`}>
                    <meta.Icon size={13} /> {meta.label}
                  </span>
                  <span className="log-server">{e.server}</span>
                  <time>{formatTime(e.timestamp)}</time>
                </span>
                <span className="log-method">{title}</span>
              </summary>
              <pre>{JSON.stringify(e.message, null, 2)}</pre>
            </details>
          );
        })}
      </div>
    </aside>
  );
}
