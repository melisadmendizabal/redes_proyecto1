"""
interfaces/web.py

Interfaz Web (API HTTP). Igual que interfaces/cli.py, es DELGADA a
propósito: no tiene lógica de negocio, solo traduce peticiones HTTP a
llamadas al Chatbot / MCPLogger / MCPManager que ya existen en core/.
El frontend de React (carpeta frontend/) consume estos endpoints.

Endpoints:
  GET  /api/status    servidores MCP conectados y sus herramientas
  GET  /api/catalog   catálogo de la farmacia (vía la tool list_medications)
  GET  /api/history   mensajes de la conversación actual (solo texto)
  POST /api/chat      {"message": "..."} -> {"reply": "...", "tool_calls": [...]}
  POST /api/reset     borra el contexto de la conversación
  GET  /api/log       log MCP (?since=N para pedir solo entradas nuevas)
"""

import os
import re
import threading

from flask import Flask, jsonify, request, send_from_directory

from core.chatbot import Chatbot, LLMClientError
from core.logger import MCPLogger
from core.mcp_manager import MCPManager

# Como la CLI, la interfaz Web es de un solo usuario: una sola sesión.
SESSION_ID = "web"

# Si corres "npm run build" en frontend/, Flask sirve ese build directamente
# (así toda la demo vive en http://localhost:5050 sin abrir Vite).
DIST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist"
)

# Línea del catálogo que devuelve list_medications, por ejemplo:
#   "- paracetamol: Q15.00 (stock: 50)"
CATALOG_LINE = re.compile(r"^-\s*(.+?):\s*Q([\d.,]+)\s*\(stock:\s*(\d+)\)", re.MULTILINE)


def create_app(bot: Chatbot, logger: MCPLogger, manager: MCPManager) -> Flask:
    app = Flask(__name__, static_folder=DIST_DIR, static_url_path="")

    # Flask atiende en varios hilos; este lock evita que dos peticiones
    # mezclen el historial de la conversación o el orden del log.
    lock = threading.Lock()

    @app.get("/api/status")
    def status():
        servers = []
        for name, tools in manager.tools_by_server.items():
            client = manager.clients[name]
            servers.append({
                "name": name,
                # Solo MCPHttpClient (servidor remoto) tiene base_url.
                "remote": hasattr(client, "base_url"),
                "tools": [
                    {"name": t["name"], "description": t.get("description", "")}
                    for t in tools
                ],
            })
        return jsonify({"servers": servers, "model": bot.llm.model})

    @app.get("/api/catalog")
    def catalog():
        # Llama directamente a la herramienta MCP del servidor de farmacia
        # (sin pasar por el LLM, así no gasta cuota de Gemini). Como es una
        # llamada MCP real, también aparece en el log.
        if "list_medications" not in manager.tool_index:
            return jsonify({"available": False, "items": []})
        try:
            with lock:
                result = manager.call_tool("list_medications", {})
        except Exception as e:
            return jsonify({"error": f"No se pudo leer el catálogo: {e}"}), 502

        text = "\n".join(c.get("text", "") for c in result.get("content", []))
        items = [
            {"name": name.strip(), "price": float(price.replace(",", "")), "stock": int(stock)}
            for name, price, stock in CATALOG_LINE.findall(text)
        ]
        return jsonify({"available": True, "items": items})

    @app.get("/api/history")
    def history():
        # Sirve para que, al recargar la página, la conversación siga
        # visible (el contexto vive en el servidor, no en el navegador).
        messages = []
        for turn in bot.get_history(SESSION_ID):
            parts = turn.get("parts", [])
            if any("functionCall" in p or "functionResponse" in p for p in parts):
                continue  # turnos intermedios de herramientas: no son mensajes
            text = "\n".join(p["text"] for p in parts if "text" in p).strip()
            if text:
                messages.append({
                    "role": "user" if turn["role"] == "user" else "bot",
                    "text": text,
                })
        return jsonify({"messages": messages})

    @app.post("/api/chat")
    def chat():
        data = request.get_json(silent=True) or {}
        text = (data.get("message") or "").strip()
        if not text:
            return jsonify({"error": "El mensaje está vacío."}), 400

        with lock:
            start = len(logger.entries)
            try:
                reply = bot.handle_message(SESSION_ID, text)
            except LLMClientError as e:
                return jsonify({"error": f"Error al llamar al modelo: {e}"}), 502
            except Exception as e:  # p. ej. un servidor MCP que se cayó
                return jsonify({"error": f"Error inesperado: {e}"}), 500
            new_entries = logger.entries[start:]

        # Qué herramientas usó el LLM en este turno: se deduce del log MCP,
        # así core/ no necesita cambiar.
        tool_calls = [
            {
                "server": e["server"],
                "name": e["message"].get("params", {}).get("name"),
                "arguments": e["message"].get("params", {}).get("arguments", {}),
            }
            for e in new_entries
            if e["direction"] == "request" and e["message"].get("method") == "tools/call"
        ]
        return jsonify({"reply": reply, "tool_calls": tool_calls})

    @app.post("/api/reset")
    def reset():
        with lock:
            bot.reset_session(SESSION_ID)
        return jsonify({"ok": True})

    @app.get("/api/log")
    def log():
        since = max(request.args.get("since", default=0, type=int), 0)
        snapshot = list(logger.entries)
        return jsonify({
            "entries": [
                {"index": i, **entry}
                for i, entry in enumerate(snapshot[since:], start=since)
            ],
            "total": len(snapshot),
        })

    @app.get("/")
    def index():
        if os.path.isfile(os.path.join(DIST_DIR, "index.html")):
            return send_from_directory(DIST_DIR, "index.html")
        return (
            "API del chatbot activa. Abre la interfaz con `npm run dev` "
            "dentro de la carpeta frontend/.",
            200,
        )

    return app


def run(bot: Chatbot, logger: MCPLogger, manager: MCPManager,
        host: str = "127.0.0.1", port: int = 5050):
    app = create_app(bot, logger, manager)
    print(f"\nAPI web lista en http://{host}:{port}")
    print("Interfaz: abre otra terminal -> cd frontend -> npm run dev\n")
    # use_reloader=False es importante: el reloader de Flask ejecutaría
    # todo el proceso dos veces y levantaría cada servidor MCP duplicado.
    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)
