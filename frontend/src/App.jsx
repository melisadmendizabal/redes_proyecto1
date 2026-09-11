import { useCallback, useEffect, useRef, useState } from "react";
import Header from "./components/Header.jsx";
import Sidebar from "./components/Sidebar.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import LogPanel from "./components/LogPanel.jsx";
import {
  getCatalog,
  getHistory,
  getLog,
  getStatus,
  resetChat,
  sendMessage,
} from "./api.js";

let nextId = 1;
const uid = () => nextId++;

export default function App() {
  const [servers, setServers] = useState([]);
  const [model, setModel] = useState("");
  const [catalog, setCatalog] = useState({ available: true, items: [] });
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [log, setLog] = useState([]);
  const [logOpen, setLogOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [online, setOnline] = useState(true);

  // --- Log MCP: se consulta cada 2 s pidiendo solo lo nuevo (?since=N) ---
  const logLen = useRef(0);
  useEffect(() => {
    logLen.current = log.length;
  }, [log]);

  const pollLog = useCallback(async () => {
    try {
      const { entries } = await getLog(logLen.current);
      setOnline(true);
      if (entries.length) {
        // Se filtra por índice por si dos consultas se traslapan.
        setLog((prev) => {
          const fresh = entries.filter((e) => e.index >= prev.length);
          return fresh.length ? [...prev, ...fresh] : prev;
        });
      }
    } catch {
      setOnline(false);
    }
  }, []);

  useEffect(() => {
    pollLog();
    const id = setInterval(pollLog, 2000);
    return () => clearInterval(id);
  }, [pollLog]);

  // --- Carga inicial ---
  const refreshCatalog = useCallback(async () => {
    setCatalogLoading(true);
    try {
      setCatalog(await getCatalog());
    } catch {
      /* si falla, se deja lo último que se tenía */
    } finally {
      setCatalogLoading(false);
    }
  }, []);

  useEffect(() => {
    getStatus()
      .then((s) => {
        setServers(s.servers);
        setModel(s.model);
        setOnline(true);
      })
      .catch(() => setOnline(false));

    getHistory()
      .then(({ messages }) =>
        setMessages(messages.map((m) => ({ id: uid(), ...m })))
      )
      .catch(() => {});

    refreshCatalog();
  }, [refreshCatalog]);

  // --- Acciones ---
  const handleSend = async (text) => {
    if (!text || loading) return;
    setMessages((m) => [...m, { id: uid(), role: "user", text }]);
    setLoading(true);
    try {
      const { reply, tool_calls } = await sendMessage(text);
      setMessages((m) => [
        ...m,
        { id: uid(), role: "bot", text: reply || "(sin respuesta)", toolCalls: tool_calls },
      ]);
      // Si se compró algo, el stock cambió: se actualiza el catálogo.
      if (tool_calls.some((t) => t.name === "purchase_medication")) refreshCatalog();
    } catch (e) {
      setMessages((m) => [...m, { id: uid(), role: "error", text: e.message }]);
    } finally {
      setLoading(false);
      pollLog();
    }
  };

  const handleReset = async () => {
    if (messages.length && !window.confirm("¿Iniciar una nueva conversación? Se borrará el contexto actual.")) {
      return;
    }
    try {
      await resetChat();
      setMessages([]);
    } catch (e) {
      setMessages((m) => [...m, { id: uid(), role: "error", text: e.message }]);
    }
  };

  return (
    <div className="app">
      <Header
        online={online}
        logCount={log.length}
        logOpen={logOpen}
        onToggleLog={() => setLogOpen((v) => !v)}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
        onReset={handleReset}
      />
      <main className={`main ${logOpen ? "log-open" : ""}`}>
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          servers={servers}
          model={model}
          catalog={catalog}
          catalogLoading={catalogLoading}
          onRefreshCatalog={refreshCatalog}
        />
        <ChatPanel
          messages={messages}
          loading={loading}
          online={online}
          onSend={handleSend}
        />
        {logOpen && <LogPanel entries={log} onClose={() => setLogOpen(false)} />}
      </main>
    </div>
  );
}
