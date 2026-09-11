"""
main_web.py

Punto de entrada de la interfaz Web. Hace lo mismo que main.py (mismos
servidores MCP, mismo Chatbot, mismo logger), pero en vez de arrancar la
CLI levanta una API HTTP que consume el frontend de React (frontend/).

Uso (desde la raíz del proyecto):  python -m main_web
"""

import os

# Importante: este import va primero porque core.llm_client carga el .env
# (GEMINI_API_KEY, PHARMACY_REMOTE_URL, ...) al importarse.
from core.chatbot import Chatbot
from core.logger import MCPLogger
from interfaces.web import run

# Reusamos la configuración de servidores de main.py: no se duplica nada.
from main import WORKSPACE_DIR, build_mcp_manager, ensure_git_repo

WEB_PORT = int(os.environ.get("WEB_PORT", 5050))


def main():
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    ensure_git_repo(WORKSPACE_DIR)

    logger = MCPLogger()

    print("Levantando servidores MCP...")
    manager = build_mcp_manager(logger)
    print(f"Herramientas disponibles: {[t['name'] for t in manager.get_all_tools()]}")

    bot = Chatbot(mcp_manager=manager)

    try:
        run(bot=bot, logger=logger, manager=manager, port=WEB_PORT)
    finally:
        manager.close_all()


if __name__ == "__main__":
    main()
