"""
core/mcp_manager.py

Orquesta varios servidores MCP a la vez. Se encarga de:
  - Levantar cada servidor y hacer su handshake.
  - Juntar las herramientas de TODOS los servidores en un solo catálogo.
  - Saber a qué servidor mandar una llamada según el nombre de la
    herramienta (el chatbot no necesita saber cuál servidor la expone).
  - Traducir las herramientas de formato MCP a formato de function
    calling de Gemini (functionDeclarations), para que el LLM pueda
    "verlas" y decidir usarlas.
"""

from core.mcp_client import MCPStdioClient, MCPClientError
from core.logger import MCPLogger


class MCPManager:
    def __init__(self, logger: MCPLogger = None):
        self.logger = logger
        self.clients: dict[str, MCPStdioClient] = {}       # server_name -> client
        self.tools_by_server: dict[str, list[dict]] = {}    # server_name -> [tool, ...]
        self.tool_index: dict[str, str] = {}                # tool_name -> server_name

    def add_server(self, server_name: str, command: list[str]) -> list[dict]:
        """
        Levanta un servidor MCP (subproceso), hace el handshake y registra
        sus herramientas. Regresa la lista de herramientas descubiertas.
        """
        client = MCPStdioClient(command=command, server_name=server_name, logger=self.logger)
        client.start()
        client.initialize()

        tools = client.list_tools()

        self.clients[server_name] = client
        self.tools_by_server[server_name] = tools

        for tool in tools:
            if tool["name"] in self.tool_index:
                # Dos servidores exponiendo una herramienta con el mismo
                # nombre es un conflicto real: el manager no sabría a
                # cuál mandar la llamada. Mejor fallar ruidosamente que
                # silenciosamente usar el servidor equivocado.
                raise MCPClientError(
                    f"Conflicto: la herramienta '{tool['name']}' ya está "
                    f"registrada por otro servidor."
                )
            self.tool_index[tool["name"]] = server_name

        return tools

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Llama a una herramienta por nombre, sin que quien llama sepa
        en qué servidor vive."""
        server_name = self.tool_index.get(name)
        if server_name is None:
            raise MCPClientError(f"Herramienta desconocida: '{name}'")
        return self.clients[server_name].call_tool(name, arguments)

    def get_all_tools(self) -> list[dict]:
        """Todas las herramientas de todos los servidores, en formato MCP crudo."""
        all_tools = []
        for tools in self.tools_by_server.values():
            all_tools.extend(tools)
        return all_tools

    def get_gemini_tools(self) -> list[dict] | None:
        """
        Convierte el catálogo de herramientas MCP a formato de function
        calling de Gemini. Si no hay ninguna herramienta registrada,
        regresa None (para no mandar un bloque "tools" vacío a la API).
        """
        all_tools = self.get_all_tools()
        if not all_tools:
            return None

        declarations = [self._mcp_tool_to_gemini(t) for t in all_tools]
        return [{"functionDeclarations": declarations}]

    @staticmethod
    def _mcp_tool_to_gemini(tool: dict) -> dict:
        """
        Un tool de MCP ya trae 'inputSchema' en formato JSON Schema
        estándar (type/properties/required), que es compatible con lo
        que Gemini espera en 'parameters'. Solo tomamos los campos que
        Gemini entiende, para evitar mandar llaves raras (ej. $schema).
        """
        schema = tool.get("inputSchema", {"type": "object", "properties": {}})
        parameters = {
            "type": schema.get("type", "object"),
            "properties": schema.get("properties", {}),
        }
        if "required" in schema:
            parameters["required"] = schema["required"]

        return {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": parameters,
        }

    def close_all(self):
        for client in self.clients.values():
            client.close()