import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { AlertTriangle, HeartPulse, Send, User, Wrench } from "lucide-react";

const SUGGESTIONS = [
  {
    label: "Tengo dolor de cabeza",
    text: "Tengo dolor de cabeza, ¿qué me recomiendas?",
  },
  {
    label: "Ver el catálogo",
    text: "¿Qué medicamentos tienen disponibles?",
  },
  {
    label: "Comprar paracetamol",
    text: "Cómprame 2 de paracetamol",
  },
  {
    label: "Crear README y commit",
    text: 'Crea un archivo README.md en el repositorio con el texto "Proyecto MCP - CC3067", agrégalo al staging y haz commit con el mensaje "initial commit"',
  },
];

function ToolChips({ calls }) {
  if (!calls || calls.length === 0) return null;
  return (
    <div className="tool-chips" aria-label="Herramientas MCP utilizadas">
      {calls.map((t, i) => (
        <span
          key={i}
          className="chip"
          title={`${t.server}\n${JSON.stringify(t.arguments, null, 2)}`}
        >
          <Wrench size={12} />
          <b>{t.name}</b>
          <em>{t.server}</em>
        </span>
      ))}
    </div>
  );
}

function Message({ m }) {
  if (m.role === "user") {
    return (
      <div className="msg user">
        <div className="bubble">{m.text}</div>
        <div className="avatar user-av" aria-hidden="true"><User size={16} /></div>
      </div>
    );
  }
  if (m.role === "error") {
    return (
      <div className="msg bot">
        <div className="avatar err-av" aria-hidden="true"><AlertTriangle size={16} /></div>
        <div className="bubble error" role="alert">{m.text}</div>
      </div>
    );
  }
  return (
    <div className="msg bot">
      <div className="avatar bot-av" aria-hidden="true"><HeartPulse size={16} /></div>
      <div className="bot-col">
        <ToolChips calls={m.toolCalls} />
        <div className="bubble">
          <ReactMarkdown>{m.text}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

function Welcome({ onPick, disabled }) {
  return (
    <div className="welcome">
      <div className="welcome-icon" aria-hidden="true"><HeartPulse size={30} /></div>
      <h2>¿En qué te puedo ayudar hoy?</h2>
      <p>
        Cuéntame tus síntomas, pregunta por un medicamento o pídeme comprarlo.
        También puedo trabajar con archivos y Git.
      </p>
      <div className="suggestions">
        {SUGGESTIONS.map((s) => (
          <button key={s.label} className="suggestion" disabled={disabled} onClick={() => onPick(s.text)}>
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ChatPanel({ messages, loading, online, onSend }) {
  const [draft, setDraft] = useState("");
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  // Siempre mostrar lo último que llegó.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  // El cuadro de texto crece con lo que se escribe (máx. ~5 líneas).
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 132)}px`;
  }, [draft]);

  const submit = () => {
    const text = draft.trim();
    if (!text || loading) return;
    setDraft("");
    onSend(text);
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <section className="card chat" aria-label="Conversación">
      {!online && (
        <div className="banner" role="alert">
          <AlertTriangle size={16} />
          Sin conexión con el servidor. Verifica que <code>python -m main_web</code> esté corriendo.
        </div>
      )}

      <div className="messages" aria-live="polite">
        {messages.length === 0 && !loading && <Welcome onPick={onSend} disabled={loading || !online} />}

        {messages.map((m) => (
          <Message key={m.id} m={m} />
        ))}

        {loading && (
          <div className="msg bot">
            <div className="avatar bot-av" aria-hidden="true"><HeartPulse size={16} /></div>
            <div className="bubble typing" aria-label="El asistente está escribiendo">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="composer">
        <div className="composer-row">
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="Escribe tu consulta…"
            aria-label="Mensaje"
          />
          <button
            className="send"
            onClick={submit}
            disabled={!draft.trim() || loading}
            aria-label="Enviar mensaje"
            title="Enviar"
          >
            <Send size={20} />
          </button>
        </div>
        <p className="disclaimer">
          Enter para enviar · Shift+Enter para nueva línea. Demostración académica: las
          recomendaciones no sustituyen la consulta con un profesional de la salud.
        </p>
      </div>
    </section>
  );
}
