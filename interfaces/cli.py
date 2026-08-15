# Interfaz de terminal. Es DELGADA a propósito: solo lee input, se lo pasa
# al Chatbot, y pinta la respuesta. No tiene lógica de negocio, ni maneja
# el historial directamente, ni sabe nada de la API de Anthropic. Toda esa
# lógica vive en core/chatbot.py.

# Esto es lo que hace que, si más adelante agregas una interfaz Web, no
# tengas que tocar core/ para nada: solo escribes otro archivo delgado
# parecido a este, pero que reciba requests HTTP en vez de input().

from core.chatbot import Chatbot, LLMClientError

# Como la CLI es de un solo usuario, usamos un session_id fijo.
SESSION_ID = "consola"

BANNER = (
    "Chatbot MCP — escribe tu mensaje y presiona Enter.\n"
    "Comandos: /reset (borra el contexto), /salir (termina el programa)\n"
)


def run():
    print(BANNER)

    try:
        bot = Chatbot()
    except LLMClientError as e:
        print(f"No se pudo iniciar el chatbot: {e}")
        return

    while True:
        try:
            user_text = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            break

        if not user_text:
            continue

        if user_text.lower() in ("/salir", "/exit", "/quit"):
            print("Hasta luego.")
            break

        if user_text.lower() == "/reset":
            bot.reset_session(SESSION_ID)
            print("(contexto reiniciado)\n")
            continue

        try:
            respuesta = bot.handle_message(SESSION_ID, user_text)
        except LLMClientError as e:
            print(f"[Error al llamar al modelo: {e}]\n")
            continue

        print(f"Bot: {respuesta}\n")


if __name__ == "__main__":
    run()