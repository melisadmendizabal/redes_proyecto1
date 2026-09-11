import {
  Cloud,
  Folder,
  GitBranch,
  HardDrive,
  PillBottle,
  RefreshCw,
  Server,
  X,
} from "lucide-react";

const SERVER_ICONS = { filesystem: Folder, git: GitBranch, pharmacy: PillBottle };
const LOW_STOCK = 10;

function Catalog({ catalog, loading, onRefresh }) {
  const maxStock = Math.max(1, ...catalog.items.map((i) => i.stock));

  return (
    <section className="card section">
      <h2 className="section-title">
        <span className="icon-wrap green"><PillBottle size={16} /></span>
        Catálogo
        <button
          className="icon-btn small push"
          onClick={onRefresh}
          disabled={loading}
          aria-label="Actualizar catálogo"
          title="Actualizar catálogo"
        >
          <RefreshCw size={15} className={loading ? "spin" : ""} />
        </button>
      </h2>

      {!catalog.available && (
        <p className="muted">El servidor de farmacia no está conectado.</p>
      )}
      {catalog.available && catalog.items.length === 0 && (
        <p className="muted">{loading ? "Cargando…" : "Sin medicamentos para mostrar."}</p>
      )}

      <ul className="meds">
        {catalog.items.map((item) => (
          <li key={item.name} className="med">
            <div className="med-top">
              <span className="med-name">{item.name}</span>
              <span className="med-price">Q{item.price.toFixed(2)}</span>
            </div>
            <div className={`stock-bar ${item.stock <= LOW_STOCK ? "low" : ""}`}>
              <span style={{ width: `${(item.stock / maxStock) * 100}%` }} />
            </div>
            <div className="med-stock">
              {item.stock <= LOW_STOCK ? "Poco stock · " : "Disponible · "}
              {item.stock} unidades
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Servers({ servers, model }) {
  return (
    <section className="card section">
      <h2 className="section-title">
        <span className="icon-wrap blue"><Server size={16} /></span>
        Servidores MCP
      </h2>

      {servers.length === 0 && <p className="muted">Sin servidores conectados.</p>}

      <ul className="servers">
        {servers.map((s) => {
          const Icon = SERVER_ICONS[s.name] || Server;
          return (
            <li key={s.name} className="server">
              <div className="server-icon"><Icon size={18} /></div>
              <div className="server-info">
                <div className="server-row">
                  <strong>{s.name}</strong>
                  <span className={`tag ${s.remote ? "remote" : "local"}`}>
                    {s.remote ? <Cloud size={12} /> : <HardDrive size={12} />}
                    {s.remote ? "remoto · HTTP" : "local · stdio"}
                  </span>
                </div>
                <details>
                  <summary>{s.tools.length} herramientas</summary>
                  <ul className="tool-list">
                    {s.tools.map((t) => (
                      <li key={t.name} title={t.description}>{t.name}</li>
                    ))}
                  </ul>
                </details>
              </div>
            </li>
          );
        })}
      </ul>

      {model && <p className="model-note">Modelo: {model}</p>}
    </section>
  );
}

export default function Sidebar({
  open,
  onClose,
  servers,
  model,
  catalog,
  catalogLoading,
  onRefreshCatalog,
}) {
  return (
    <>
      {open && <div className="backdrop" onClick={onClose} />}
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <button className="icon-btn only-mobile close-sidebar" onClick={onClose} aria-label="Cerrar panel">
          <X size={20} />
        </button>
        <Catalog catalog={catalog} loading={catalogLoading} onRefresh={onRefreshCatalog} />
        <Servers servers={servers} model={model} />
      </aside>
    </>
  );
}
