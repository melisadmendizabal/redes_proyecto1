# Guarda y muestra un log de todas las solicitudes y respuestas
# intercambiadas con los servidores MCP (requisito 3 del proyecto).

# Ahora mismo no hay ningún servidor MCP conectado todavía, así que esto
# está "vacío" en la práctica — pero la estructura queda lista para que,
# cuando escribas mcp_client.py, cada mensaje JSON-RPC que mandes o
# recibas pase por aquí (log_request / log_response / log_notification).

# Diseño: cada entrada guarda el mensaje JSON-RPC tal cual (crudo), más
# metadatos (hacia dónde va, timestamp, servidor). Así el log sirve tanto
# para mostrarlo en consola como para el reporte final (punto 7 y 9).


import json
import os
from datetime import datetime, timezone


class MCPLogger:
    def __init__(self, log_to_file: bool = True, log_dir: str = "logs"):
        # Todo el log también vive en memoria, para poder mostrarlo con
        # un comando tipo /log sin tener que releer el archivo.
        self.entries: list[dict] = []

        self.log_to_file = log_to_file
        self.log_dir = log_dir
        self.log_path = None

        if self.log_to_file:
            os.makedirs(self.log_dir, exist_ok=True)
            filename = datetime.now().strftime("mcp_%Y%m%d_%H%M%S.jsonl")
            self.log_path = os.path.join(self.log_dir, filename)

    # --- API pública que usará mcp_client.py más adelante ---

    def log_request(self, server_name: str, message: dict):
        #Un JSON-RPC request que TÚ mandas hacia un servidor MCP.
        self._add_entry("request", server_name, message)

    def log_response(self, server_name: str, message: dict):
        #Un JSON-RPC response que un servidor MCP te regresa.
        self._add_entry("response", server_name, message)

    def log_notification(self, server_name: str, message: dict):
        #Un JSON-RPC notification (no espera respuesta, ej. 'initialized').
        self._add_entry("notification", server_name, message)

    def log_error(self, server_name: str, message: dict):
        #Un JSON-RPC error response.
        self._add_entry("error", server_name, message)



    def _add_entry(self, direction: str, server_name: str, message: dict):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "direction": direction,       # request | response | notification | error
            "server": server_name,        # ej. "filesystem", "git", "my_server"
            "message": message,           # el JSON-RPC crudo
        }
        self.entries.append(entry)

        if self.log_to_file:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # visualización 

    def get_entries(self, server_name: str = None, limit: int = None) -> list[dict]:
        result = self.entries
        if server_name:
            result = [e for e in result if e["server"] == server_name]
        if limit:
            result = result[-limit:]
        return result

    def print_log(self, server_name: str = None, limit: int = 20):
        #Muestra el log en consola de forma legible (requisito: 'mostrar' el log).
        entries = self.get_entries(server_name=server_name, limit=limit)

        if not entries:
            print("(sin interacciones MCP registradas todavía)")
            return

        for e in entries:
            direction_tag = {
                "request": "-->",
                "response": "<--",
                "notification": "..",
                "error": "!!",
            }.get(e["direction"], "??")

            method = e["message"].get("method", e["message"].get("result", ""))
            print(f"[{e['timestamp']}] {direction_tag} ({e['server']}) {method}")
            print(f"    {json.dumps(e['message'], ensure_ascii=False)}")


# Prueba rápida 
if __name__ == "__main__":
    logger = MCPLogger(log_to_file=True)

    logger.log_request("filesystem", {
        "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
    })
    logger.log_response("filesystem", {
        "jsonrpc": "2.0", "id": 1,
        "result": {"tools": [{"name": "read_file"}, {"name": "write_file"}]}
    })

    logger.print_log()
    print(f"\nLog guardado en: {logger.log_path}")