"""
servers/pharmacy/logic.py

Lógica de negocio pura del servidor de farmacia: el catálogo, la
definición de herramientas (en formato MCP), y las funciones que las
implementan. Este archivo NO sabe nada de stdio ni de HTTP — por eso lo
pueden compartir local_stdio.py y remote_http.py sin duplicar código.
"""

PROTOCOL_VERSION = "2025-11-25"
SERVER_INFO = {"name": "pharmacy-mcp-server", "version": "0.1.0"}

# "Base de datos" en memoria, compartida por cualquier transporte que
# use este módulo.
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


def dispatch_tool_call(name: str, arguments: dict) -> dict:
    """Punto único de entrada para ejecutar una herramienta por nombre.
    Usado igual por el transporte stdio y por el HTTP."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        raise KeyError(f"Herramienta desconocida: {name}")
    return handler(arguments or {})
