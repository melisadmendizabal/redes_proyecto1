"""
core/chatbot.py

El "cerebro" del proyecto. Mantiene el historial de conversación por
sesión (para cumplir el requisito de "mantener contexto") y usa
llm_client.py para hablar con la API de Gemini.

No sabe nada de terminal ni de Web: cualquier interfaz (cli.py, o más
adelante una API web) solo importa la clase Chatbot y llama a
handle_message().

OJO con el formato: Gemini usa rol "model" para las respuestas del
asistente (no "assistant" como Anthropic/OpenAI), y cada mensaje va
envuelto en una lista "parts". Por eso Session arma los mensajes así.
"""

from core.llm_client import LLMClient, LLMClientError

DEFAULT_SYSTEM_PROMPT = (
    "Eres un asistente útil que responde preguntas y, cuando esté "
    "disponible, puede usar herramientas externas para realizar acciones."
)


class Session:
    """
    Representa el historial de UNA conversación, en el formato que espera
    la API de Gemini (lista de {"role": ..., "parts": [{"text": ...}]}).
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.contents: list[dict] = []

    def add_user_message(self, text: str):
        self.contents.append({"role": "user", "parts": [{"text": text}]})

    def add_model_message(self, text: str):
        self.contents.append({"role": "model", "parts": [{"text": text}]})

    def get_history(self) -> list[dict]:
        # Copia para que nadie modifique el historial real por accidente.
        return list(self.contents)


class Chatbot:
    def __init__(self, system_prompt: str = DEFAULT_SYSTEM_PROMPT):
        self.llm = LLMClient()
        self.system_prompt = system_prompt
        # Todas las sesiones activas viven en memoria mientras el proceso
        # corre. Útil desde ya para cuando conectes múltiples usuarios
        # en una futura interfaz Web (cada uno con su propio session_id).
        self._sessions: dict[str, Session] = {}

    def _get_or_create_session(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id)
        return self._sessions[session_id]

    def handle_message(self, session_id: str, user_text: str) -> str:
        """
        Recibe el id de sesión y el mensaje del usuario, actualiza el
        historial de esa sesión, llama al LLM con el historial completo
        (por eso mantiene contexto) y regresa la respuesta en texto.
        """
        session = self._get_or_create_session(session_id)
        session.add_user_message(user_text)

        respuesta_texto = self.llm.get_text_response(
            contents=session.get_history(),
            system_instruction=self.system_prompt,
        )

        session.add_model_message(respuesta_texto)
        return respuesta_texto

    def reset_session(self, session_id: str):
        """Borra el historial de una sesión (útil para un comando /reset)."""
        self._sessions[session_id] = Session(session_id)

    def get_history(self, session_id: str) -> list[dict]:
        return self._get_or_create_session(session_id).get_history()


# --- Prueba rápida manual ---
if __name__ == "__main__":
    bot = Chatbot()
    sid = "sesion-de-prueba"

    print(bot.handle_message(sid, "¿Quién fue Alan Turing?"))
    print("---")
    # Esta segunda pregunta solo tiene sentido si el bot mantiene contexto:
    print(bot.handle_message(sid, "¿En qué fecha nació?"))