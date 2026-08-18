"""
core/mcp_client.py

Cliente MCP implementado a mano (sin SDKs de MCP), hablando JSON-RPC 2.0
sobre stdio con un servidor MCP que corre como subproceso.

Reglas del transporte stdio (de la spec) que este archivo respeta:
  - Un mensaje JSON-RPC completo por línea (newline-delimited).
  - Nunca saltos de línea embebidos dentro de un mensaje.
  - stderr del servidor es solo para logs de debug, nunca protocolo.

Ciclo de vida que implementa:
  initialize (request) -> notifications/initialized (notification)
  -> ya se puede usar tools/list y tools/call.
"""

import json
import shutil
import subprocess
import threading

from core.logger import MCPLogger

MCP_PROTOCOL_VERSION = "2025-11-25"


class MCPClientError(Exception):
    """Error de protocolo o de comunicación con un servidor MCP."""
    pass


class MCPStdioClient:
    def __init__(self, command: list[str], server_name: str, logger: MCPLogger = None):
        """
        command: lista de argv para levantar el servidor, ej.
            ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/ruta"]
        server_name: nombre corto para identificar este servidor en el log
            (ej. "filesystem", "git", "my_server").
        """
        self.command = command
        self.server_name = server_name
        self.logger = logger
        self.process: subprocess.Popen | None = None
        self._next_id = 1
        self._lock = threading.Lock()  # una request a la vez por servidor

    # --- Ciclo de vida del proceso ---

    def start(self):
        # En Windows, comandos como "npx" o "npm" en realidad son
        # archivos .cmd, y subprocess.Popen no los resuelve solo como sí
        # lo hace la terminal. shutil.which() busca en el PATH respetando
        # PATHEXT (.EXE, .CMD, .BAT, etc.) y regresa la ruta completa
        # correcta. En Mac/Linux esto no cambia nada (ya funcionaba).
        resolved_executable = shutil.which(self.command[0])
        command = (
            [resolved_executable] + self.command[1:]
            if resolved_executable
            else self.command
        )

        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # line-buffered
        )
        # Drenamos stderr en un hilo aparte: son logs de debug del
        # servidor, no protocolo, pero si no los leemos el pipe se puede
        # llenar y trabar el proceso.
        threading.Thread(target=self._drain_stderr, daemon=True).start()

    def _drain_stderr(self):
        for line in self.process.stderr:
            print(f"[{self.server_name} stderr] {line.rstrip()}")

    def close(self):
        if self.process and self.process.poll() is None:
            self.process.stdin.close()
            self.process.terminate()

    # --- Framing: un JSON por línea, sin saltos de línea internos ---

    def _write_line(self, message: dict):
        line = json.dumps(message, ensure_ascii=False)
        if "\n" in line:
            raise MCPClientError("Mensaje con salto de línea embebido (viola framing)")
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()

    def _read_line(self) -> dict:
        raw = self.process.stdout.readline()
        if raw == "":
            raise MCPClientError(f"El servidor '{self.server_name}' cerró la conexión")
        return json.loads(raw)

    def _next_request_id(self) -> int:
        rid = self._next_id
        self._next_id += 1
        return rid

    # --- Envío de mensajes JSON-RPC ---

    def send_request(self, method: str, params: dict = None) -> dict:
        """Manda un request y bloquea hasta recibir su response."""
        with self._lock:
            req_id = self._next_request_id()
            message = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params or {},
            }

            if self.logger:
                self.logger.log_request(self.server_name, message)
            self._write_line(message)

            response = self._read_line()

            if response.get("id") != req_id:
                raise MCPClientError(
                    f"Respuesta con id inesperado (esperaba {req_id}, "
                    f"llegó {response.get('id')})"
                )

            if "error" in response:
                if self.logger:
                    self.logger.log_error(self.server_name, response)
                raise MCPClientError(f"Error MCP en '{method}': {response['error']}")

            if self.logger:
                self.logger.log_response(self.server_name, response)

            return response.get("result", {})

    def send_notification(self, method: str, params: dict = None):
        """Manda una notification (no espera ni lee respuesta)."""
        message = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if self.logger:
            self.logger.log_notification(self.server_name, message)
        self._write_line(message)

    # --- Métodos de alto nivel del protocolo MCP ---

    def initialize(self, client_name: str = "mi-chatbot", client_version: str = "0.1.0") -> dict:
        result = self.send_request("initialize", {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": client_name, "version": client_version},
        })
        # El handshake se cierra con esta notification, según el lifecycle.
        self.send_notification("notifications/initialized")
        return result

    def list_tools(self) -> list[dict]:
        result = self.send_request("tools/list")
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: dict = None) -> dict:
        return self.send_request("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })


# --- Prueba manual: requiere Node.js instalado (para npx) ---
if __name__ == "__main__":
    logger = MCPLogger()

    # Ejemplo con el Filesystem MCP server oficial, apuntando a una carpeta
    # de prueba. Ajusta la ruta a algo que exista en tu máquina.
    client = MCPStdioClient(
        command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."],
        server_name="filesystem",
        logger=logger,
    )

    try:
        client.start()

        info = client.initialize()
        print("Servidor inicializado:", info.get("serverInfo"))

        tools = client.list_tools()
        print("Herramientas disponibles:")
        for t in tools:
            print(f"  - {t['name']}: {t.get('description', '')}")

    finally:
        client.close()
        logger.print_log()