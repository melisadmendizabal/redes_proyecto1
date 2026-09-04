"""
servers/pharmacy/remote_http.py

Adaptador de transporte HTTP (Streamable HTTP, según la spec MCP
2025-11-25) para el mismo servidor de farmacia. Reusa exactamente la
misma lógica de negocio de logic.py — lo único que cambia es CÓMO
viajan los mensajes JSON-RPC: por HTTP en vez de stdin/stdout.

Implementación simplificada de Streamable HTTP para este proyecto:
  - Un solo endpoint: POST /mcp
  - Modo de "respuesta única" (un JSON por respuesta), sin SSE — el
    modo SSE es opcional en la spec para streaming; aquí no hace falta
    porque nuestras herramientas responden de inmediato.
  - Sesión manejada con el header Mcp-Session-Id: el servidor la asigna
    en la respuesta de 'initialize', y el cliente debe reenviarla en
    cada petición siguiente.
  - Las notifications (sin "id") responden 202 Accepted sin cuerpo,
    tal como indica la spec.

No se usa ningún SDK de MCP — Flask es solo un framework HTTP genérico,
el manejo del protocolo JSON-RPC/MCP en sí está escrito a mano abajo.

Correr localmente con: python -m servers.pharmacy.remote_http
"""

import uuid
from flask import Flask, request, jsonify, Response

from servers.pharmacy import logic

app = Flask(__name__)

# Sesiones activas: session_id -> True (aquí solo verificamos que exista;
# se podría guardar más estado por sesión si se necesitara).
ACTIVE_SESSIONS = set()


def error_response(req_id, code, message, http_status=200):
    body = {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
    return jsonify(body), http_status


def handle_initialize(req_id) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": logic.PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": logic.SERVER_INFO,
        },
    }


def handle_tools_list(req_id) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": logic.TOOLS}}


def handle_tools_call(req_id, params: dict) -> dict:
    name = params.get("name")
    arguments = params.get("arguments", {})
    try:
        result = logic.dispatch_tool_call(name, arguments)
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    except KeyError as e:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": str(e)}}
    except Exception as e:
        return {
            "jsonrpc": "2.0", "id": req_id,
            "error": {"code": -32000, "message": f"Error ejecutando '{name}': {e}"},
        }


@app.route("/mcp", methods=["POST"])
def mcp_endpoint():
    message = request.get_json(silent=True)
    if message is None:
        return error_response(None, -32700, "Parse error: cuerpo no es JSON válido", http_status=400)

    method = message.get("method")
    req_id = message.get("id")  # None si es notification
    session_id = request.headers.get("Mcp-Session-Id")

    # Toda petición que NO sea 'initialize' debe traer una sesión válida.
    if method != "initialize":
        if not session_id or session_id not in ACTIVE_SESSIONS:
            return jsonify({
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32000, "message": "Falta o es inválido el header Mcp-Session-Id"},
            }), 400

    if method == "initialize":
        new_session_id = str(uuid.uuid4())
        ACTIVE_SESSIONS.add(new_session_id)
        body = handle_initialize(req_id)
        response = jsonify(body)
        response.headers["Mcp-Session-Id"] = new_session_id
        return response, 200

    if method == "notifications/initialized":
        # Notification: no lleva "id", no se responde cuerpo.
        return Response(status=202)

    if method == "tools/list":
        return jsonify(handle_tools_list(req_id)), 200

    if method == "tools/call":
        return jsonify(handle_tools_call(req_id, message.get("params", {}))), 200

    if req_id is not None:
        return jsonify({
            "jsonrpc": "2.0", "id": req_id,
            "error": {"code": -32601, "message": f"Método no soportado: {method}"},
        }), 200

    # Notification desconocida: se ignora.
    return Response(status=202)


@app.route("/health", methods=["GET"])
def health():
    """Endpoint simple para que Cloud Run confirme que el contenedor está vivo."""
    return jsonify({"status": "ok", "server": logic.SERVER_INFO["name"]}), 200


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
