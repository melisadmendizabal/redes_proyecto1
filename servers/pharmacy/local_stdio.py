"""
servers/pharmacy/local_stdio.py

Servidor MCP propio para el caso de uso de una cadena de farmacias.
Implementado a mano (sin SDK de MCP), hablando JSON-RPC 2.0 por stdio:
lee un mensaje JSON por línea de stdin, escribe la respuesta como un
JSON por línea en stdout. stderr se usa solo para logs de debug.

Este archivo se ejecuta como PROCESO INDEPENDIENTE (tu chatbot lo levanta
como subproceso usando la misma MCPStdioClient que ya tienes). Corre:
    python -m servers.pharmacy.local_stdio

Herramientas expuestas:
  - search_by_symptom(symptom: str) -> lista de medicamentos sugeridos
  - get_medication_info(name: str)   -> detalle de un medicamento
  - list_medications()                -> catálogo completo
  - purchase_medication(name, quantity) -> simula una compra y baja stock
"""

import sys
import json

PROTOCOL_VERSION = "2025-11-25"

# "Base de datos" en memoria. Para el proyecto es suficiente; si luego
# quieres persistencia real, aquí es donde conectarías un archivo o DB.
CATALOG = {
    "paracetamol": {
        "description": "Analgésico y antipirético, para dolor leve y fiebre.",
        "symptoms": ["dolor de cabeza", "fiebre", "dolor muscular"],
        "price": 15.0,
        "stock": 50,
    },
    "ibuprofeno": {
        "description": "Antiinflamatorio no esteroideo, para dolor e inflamación.",
        "symptoms": ["dolor de cabeza", "dolor muscular", "inflamación"],
        "price": 20.0,
        "stock": 40,
    },
    "loratadina": {
        "description": "Antihistamínico, para alergias.",
        "symptoms": ["alergia", "estornudos", "picazón"],
        "price": 18.0,
        "stock": 30,
    },
    "omeprazol": {
        "description": "Inhibidor de ácido gástrico, para acidez estomacal.",
        "symptoms": ["acidez", "dolor de estómago", "gastritis"],
        "price": 25.0,
        "stock": 25,
    },
}

# Definición de las herramientas en formato MCP (esto es lo que
# tools/list debe regresar).
TOOLS = [
    {
        "name": "search_by_symptom",
        "description": "Busca medicamentos recomendados según un síntoma descrito por el cliente.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symptom": {"type": "string", "description": "Síntoma del cliente, ej. 'dolor de cabeza'"}
            },
            "required": ["symptom"],
        },
    },
    {
        "name": "get_medication_info",
        "description": "Regresa la descripción, precio y stock de un medicamento por nombre.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nombre del medicamento"}
            },
            "required": ["name"],
        },
    },
    {
        "name": "list_medications",
        "description": "Lista todo el catálogo de medicamentos disponibles.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "purchase_medication",
        "description": "Compra una cantidad de un medicamento, si hay stock suficiente.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "quantity": {"type": "integer", "minimum": 1},
            },
            "required": ["name", "quantity"],
        },
    },
]


def log(msg: str):
    """Log de debug: SIEMPRE a stderr, nunca a stdout (romperías el framing)."""
    print(f"[pharmacy-server] {msg}", file=sys.stderr, flush=True)


# --- Lógica de negocio de cada herramienta ---

def tool_search_by_symptom(arguments: dict) -> dict:
    symptom = arguments.get("symptom", "").lower().strip()
    matches = [
        {"name": name, **data}
        for name, data in CATALOG.items()
        if any(symptom in s for s in data["symptoms"])
    ]
    if not matches:
        text = f"No se encontraron medicamentos para el síntoma '{symptom}'."
    else:
        nombres = ", ".join(m["name"] for m in matches)
        text = f"Para '{symptom}' se recomienda: {nombres}."
    return {"content": [{"type": "text", "text": text}], "isError": False}


def tool_get_medication_info(arguments: dict) -> dict:
    name = arguments.get("name", "").lower().strip()
    if name not in CATALOG:
        return {
            "content": [{"type": "text", "text": f"No existe el medicamento '{name}'."}],
            "isError": True,
        }
    data = CATALOG[name]
    text = (
        f"{name.capitalize()}: {data['description']} "
        f"Precio: Q{data['price']:.2f}. Stock disponible: {data['stock']}."
    )
    return {"content": [{"type": "text", "text": text}], "isError": False}


def tool_list_medications(arguments: dict) -> dict:
    lines = [
        f"- {name}: Q{data['price']:.2f} (stock: {data['stock']})"
        for name, data in CATALOG.items()
    ]
    text = "Catálogo disponible:\n" + "\n".join(lines)
    return {"content": [{"type": "text", "text": text}], "isError": False}


def tool_purchase_medication(arguments: dict) -> dict:
    name = arguments.get("name", "").lower().strip()
    quantity = arguments.get("quantity", 0)

    if name not in CATALOG:
        return {
            "content": [{"type": "text", "text": f"No existe el medicamento '{name}'."}],
            "isError": True,
        }

    data = CATALOG[name]
    if quantity <= 0 or data["stock"] < quantity:
        text = f"No hay stock suficiente de {name}. Disponible: {data['stock']}."
        return {"content": [{"type": "text", "text": text}], "isError": True}

    data["stock"] -= quantity
    total = data["price"] * quantity
    text = f"Compra confirmada: {quantity} x {name} = Q{total:.2f}. Stock restante: {data['stock']}."
    return {"content": [{"type": "text", "text": text}], "isError": False}


TOOL_HANDLERS = {
    "search_by_symptom": tool_search_by_symptom,
    "get_medication_info": tool_get_medication_info,
    "list_medications": tool_list_medications,
    "purchase_medication": tool_purchase_medication,
}


# --- Servidor JSON-RPC manual ---

def write_message(message: dict):
    line = json.dumps(message, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def handle_initialize(req_id, params: dict) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "pharmacy-mcp-server", "version": "0.1.0"},
        },
    }


def handle_tools_list(req_id) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}


def handle_tools_call(req_id, params: dict) -> dict:
    name = params.get("name")
    arguments = params.get("arguments", {})

    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Herramienta desconocida: {name}"},
        }

    try:
        result = handler(arguments)
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32000, "message": f"Error ejecutando '{name}': {e}"},
        }


def main():
    log("Servidor de farmacia iniciado, esperando mensajes por stdin...")

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
        req_id = message.get("id")  # None si es notification

        log(f"Recibido: method={method} id={req_id}")

        if method == "initialize":
            write_message(handle_initialize(req_id, message.get("params", {})))

        elif method == "notifications/initialized":
            # Es una notification: no se responde nada.
            log("Cliente confirmó inicialización.")

        elif method == "tools/list":
            write_message(handle_tools_list(req_id))

        elif method == "tools/call":
            write_message(handle_tools_call(req_id, message.get("params", {})))

        elif req_id is not None:
            # Cualquier otro método con id: responder error "no soportado".
            write_message({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Método no soportado: {method}"},
            })
        # Si era notification desconocida, simplemente se ignora.


if __name__ == "__main__":
    main()