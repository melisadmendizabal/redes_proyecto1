import { Cross, Menu, RotateCcw, ScrollText } from "lucide-react";

export default function Header({
  online,
  logCount,
  logOpen,
  onToggleLog,
  onToggleSidebar,
  onReset,
}) {
  return (
    <header className="header">
      <button
        className="icon-btn only-mobile"
        onClick={onToggleSidebar}
        aria-label="Abrir catálogo y servidores"
      >
        <Menu size={20} />
      </button>

      <div className="brand">
        <div className="brand-logo" aria-hidden="true">
          <Cross size={22} strokeWidth={3} />
        </div>
        <div>
          <h1>Farmacia MCP</h1>
          <p>Asistente farmacéutico · Model Context Protocol</p>
        </div>
      </div>

      <div className="header-actions">
        <span className={`status-pill ${online ? "ok" : "off"}`} role="status">
          <span className="dot" />
          {online ? "Conectado" : "Sin conexión"}
        </span>

        <button className="btn ghost" onClick={onReset} title="Nueva conversación">
          <RotateCcw size={16} />
          <span className="label">Nueva conversación</span>
        </button>

        <button
          className={`btn ${logOpen ? "solid" : "soft"}`}
          onClick={onToggleLog}
          aria-pressed={logOpen}
          title="Ver el registro de mensajes MCP"
        >
          <ScrollText size={16} />
          <span className="label">Log MCP</span>
          <span className="badge">{logCount}</span>
        </button>
      </div>
    </header>
  );
}
