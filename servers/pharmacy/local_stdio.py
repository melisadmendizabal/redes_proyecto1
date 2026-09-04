"""
servers/pharmacy/local_stdio.py

Adaptador de transporte STDIO para el servidor de farmacia. Toda la
lógica de negocio real vive en logic.py — este archivo solo se encarga
de leer/escribir JSON-RPC por stdin/stdout, exactamente igual que antes.

Correr con: python -m servers.pharmacy.local_stdio
"""

import sys
import json

from servers.pharmacy import logic


def log(msg: str):
    """Log de debug: SIEMPRE a stderr, nunca a stdout (rompería el framing)."""
    print(f"[pharmacy-stdio] {msg}", file=sys.stderr, flush=True)


def write_message(message: dict):
    line = json.dumps(message, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


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
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32000, "message": f"Error ejecutando '{name}': {e}"},
        }


def main():
    log("Servidor de farmacia (stdio) iniciado, esperando mensajes por stdin...")

    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        try:
            message = json.loads(raw_line)
        except json.JSONDecodeError:
            log(f"Línea no es JSON válido, se ignora: {raw_line}")
            continue

        method = message.get("method")
        req_id = message.get("id")

        log(f"Recibido: method={method} id={req_id}")

        if method == "initialize":
            write_message(handle_initialize(req_id))
        elif method == "notifications/initialized":
            log("Cliente confirmó inicialización.")
        elif method == "tools/list":
            write_message(handle_tools_list(req_id))
        elif method == "tools/call":
            write_message(handle_tools_call(req_id, message.get("params", {})))
        elif req_id is not None:
            write_message({
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Método no soportado: {method}"},
            })


if __name__ == "__main__":
    main()
