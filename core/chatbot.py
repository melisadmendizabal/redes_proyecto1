"""
core/chatbot.py

El "cerebro" del proyecto. Mantiene el historial de conversación por
sesión, habla con Gemini vía llm_client.py, y si se le pasa un
MCPManager, es capaz de dejar que el LLM decida usar herramientas MCP
(function calling) para responder.

No sabe nada de terminal ni de Web: cualquier interfaz solo importa
Chatbot y llama a handle_message().

Ciclo de function calling con Gemini (resumen):
  1. Mandas el historial + el catálogo de herramientas ("tools").
  2. Si el modelo quiere usar una, la respuesta trae un part
     "functionCall" (no texto final todavía).
  3. Ejecutas esa herramienta de verdad (contra el servidor MCP
     correspondiente, vía MCPManager).
  4. Le mandas el resultado de vuelta como un part "functionResponse".
  5. El modelo usa ese resultado para dar la respuesta final en texto.
  Puede repetirse varias veces si encadena varias herramientas.
"""

from core.llm_client import LLMClient, LLMClientError
from core.mcp_manager import MCPManager

DEFAULT_SYSTEM_PROMPT = (
    "Eres un asistente útil que responde preguntas y, cuando esté "
    "disponible, puede usar herramientas externas para realizar acciones "
    "concretas (archivos, git, farmacia, etc.) en vez de solo describirlas. "
    "Ve directo a la acción que te piden: no llames herramientas de solo "
    "consulta (como revisar el estado o listar directorios) a menos que "
    "sea necesario para completar la tarea o que el usuario lo pida "
    "explícitamente. Cada llamada a herramienta tiene un costo, así que "
    "actúa de forma directa y eficiente."
)

# Límite de vueltas del ciclo de herramientas. Gemini a veces pide una
# sola herramienta por turno en vez de agrupar varias, así que una tarea
# encadenada (crear archivo -> git add -> git commit) puede consumir
# varias vueltas fácilmente. 10 da margen sin arriesgar un loop eterno.
MAX_TOOL_ITERATIONS = 10


class Session:
    """Historial de UNA conversación, en formato Gemini (role/parts)."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.contents: list[dict] = []

    def add_user_text(self, text: str):
        self.contents.append({"role": "user", "parts": [{"text": text}]})

    def add_model_parts(self, parts: list[dict]):
        """Agrega tal cual el turno del modelo (puede traer texto y/o functionCall)."""
        self.contents.append({"role": "model", "parts": parts})

    def add_function_responses(self, response_parts: list[dict]):
        """Agrega los resultados de ejecutar una o más herramientas."""
        self.contents.append({"role": "user", "parts": response_parts})

    def get_history(self) -> list[dict]:
        return list(self.contents)


class Chatbot:
    def __init__(
        self,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        mcp_manager: MCPManager = None,
    ):
        self.llm = LLMClient()
        self.system_prompt = system_prompt
        self.mcp_manager = mcp_manager
        self._sessions: dict[str, Session] = {}

    def _get_or_create_session(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id)
        return self._sessions[session_id]

    def handle_message(self, session_id: str, user_text: str) -> str:
        session = self._get_or_create_session(session_id)
        session.add_user_text(user_text)

        tools = self.mcp_manager.get_gemini_tools() if self.mcp_manager else None

        for _ in range(MAX_TOOL_ITERATIONS):
            data = self.llm.send_message(
                contents=session.get_history(),
                system_instruction=self.system_prompt,
                tools=tools,
            )

            try:
                candidate = data["candidates"][0]
                parts = candidate["content"]["parts"]
            except (KeyError, IndexError):
                raise LLMClientError(f"Respuesta inesperada de Gemini: {data}")

            function_calls = [p["functionCall"] for p in parts if "functionCall" in p]

            if not function_calls:
                # No quiere usar herramientas: esta es la respuesta final.
                final_text = "\n".join(p["text"] for p in parts if "text" in p)
                session.add_model_parts(parts)
                return final_text

            # El modelo pidió usar una o más herramientas: guardamos su
            # turno tal cual (incluye los functionCall) y las ejecutamos.
            session.add_model_parts(parts)

            response_parts = []
            for call in function_calls:
                name = call["name"]
                arguments = call.get("args", {})
                try:
                    result = self.mcp_manager.call_tool(name, arguments)
                except Exception as e:
                    result = {"error": str(e)}

                response_parts.append({
                    "functionResponse": {"name": name, "response": result}
                })

            session.add_function_responses(response_parts)
            # Vuelve a empezar el for: se manda todo de nuevo al modelo,
            # ahora con el resultado de la herramienta ya incluido.

        raise LLMClientError(
            "Se alcanzó el límite de iteraciones de herramientas sin "
            "obtener una respuesta final del modelo."
        )

    def reset_session(self, session_id: str):
        self._sessions[session_id] = Session(session_id)

    def get_history(self, session_id: str) -> list[dict]:
        return self._get_or_create_session(session_id).get_history()


# --- Prueba rápida manual (sin MCP, solo confirma que el chat simple sigue vivo) ---
if __name__ == "__main__":
    bot = Chatbot()
    sid = "sesion-de-prueba"

    print(bot.handle_message(sid, "¿Quién fue Alan Turing?"))
    print("---")
    print(bot.handle_message(sid, "¿En qué fecha nació?"))
    