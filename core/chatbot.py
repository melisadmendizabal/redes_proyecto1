# El "cerebro" del proyecto. Mantiene el historial de conversación por
# sesión (para cumplir el requisito de "mantener contexto") y usa
# llm_client.py para hablar con la API de Anthropic.

# No sabe nada de terminal ni de Web: cualquier interfaz (cli.py, o más
# adelante una API web) solo importa la clase Chatbot y llama a
# handle_message(). Así puedes reusar esto sin tocarlo cuando agregues UI.


from core.llm_client import LLMClient

DEFAULT_SYSTEM_PROMPT = (
    "Eres un asistente útil que responde preguntas y, cuando esté "
    "disponible, puede usar herramientas externas para realizar acciones."
)


# Representa el historial de UNA conversación. Un chatbot puede manejar
# varias sesiones al mismo tiempo (por ejemplo, si más adelante lo
# conectas a una interfaz Web con múltiples usuarios).
class Session:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: list[dict] = []

    def add_user_message(self, text: str):
        self.messages.append({"role": "user", "content": text})

    def add_assistant_message(self, text: str):
        self.messages.append({"role": "assistant", "content": text})

    def get_history(self) -> list[dict]:
        # Se manda una copia para que nadie modifique el historial real
        # por accidente desde afuera.
        return list(self.messages)


class Chatbot:
    def __init__(self, system_prompt: str = DEFAULT_SYSTEM_PROMPT):
        self.llm = LLMClient()
        self.system_prompt = system_prompt
        # Todas las sesiones activas viven en memoria mientras el proceso
        # corre. Si necesitas persistencia entre ejecuciones, aquí es
        # donde luego agregarías guardar/cargar de un archivo o DB.
        self._sessions: dict[str, Session] = {}

    def _get_or_create_session(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id)
        return self._sessions[session_id]

    def handle_message(self, session_id: str, user_text: str) -> str:
        
        # Punto de entrada principal. Recibe el id de sesión y el mensaje del usuario, actualiza el historial 
        # de esa sesión, llama al LLM con el historial completo y regresa la respuesta en texto.
        
        session = self._get_or_create_session(session_id)
        session.add_user_message(user_text)

        respuesta_texto = self.llm.get_text_response(
            messages=session.get_history(),
            system=self.system_prompt,
        )

        session.add_assistant_message(respuesta_texto)
        return respuesta_texto

    def reset_session(self, session_id: str):
        #Borra el historial de una sesión (útil para un comando /reset).
        self._sessions[session_id] = Session(session_id)

    def get_history(self, session_id: str) -> list[dict]:
        return self._get_or_create_session(session_id).get_history()


# prueba
if __name__ == "__main__":
    bot = Chatbot()
    sid = "sesion-de-prueba"

    print(bot.handle_message(sid, "¿Quién fue Alan Turing?"))
    print("---")
    # Esta segunda pregunta solo tiene sentido si el bot mantiene contexto:
    print(bot.handle_message(sid, "¿En qué fecha nació?"))