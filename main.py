"""
main.py

Punto de entrada del proyecto. Aquí (y solo aquí) se decide qué
servidores MCP existen y se arma todo antes de arrancar la interfaz.
Ni core/ ni interfaces/ saben nada de esta configuración específica —
por eso agregar/quitar un servidor MCP es cambiar solo este archivo.
"""

import os
import subprocess

from core.logger import MCPLogger
from core.mcp_manager import MCPManager
from core.chatbot import Chatbot
from interfaces.cli import run

# Una sola carpeta compartida: el Filesystem server puede leer/escribir
# archivos aquí, y el Git server versiona ese mismo contenido. Así la
# demo (crear archivo -> commit) ocurre en el mismo lugar.
WORKSPACE_DIR = os.path.abspath("./workspace")


def build_mcp_manager(logger: MCPLogger) -> MCPManager:
    manager = MCPManager(logger=logger)

    # Filesystem MCP server oficial (necesita Node.js/npm).
    manager.add_server(
        server_name="filesystem",
        command=["npx", "-y", "@modelcontextprotocol/server-filesystem", WORKSPACE_DIR],
    )

    # Git MCP server oficial, instalado vía pip. Apunta a LA MISMA carpeta.
    manager.add_server(
        server_name="git",
        command=["python", "-m", "mcp_server_git", "--repository", WORKSPACE_DIR],
    )

    # Tu servidor propio (farmacia).
    manager.add_server(
        server_name="pharmacy",
        command=["python", "-m", "servers.pharmacy.local_stdio"],
    )

    return manager


def ensure_git_repo(path: str):
    """Si la carpeta no tiene un repo git válido, lo inicializa. Así,
    si borras workspace/ para empezar limpio, no tienes que acordarte
    de correr 'git init' a mano otra vez."""
    if not os.path.isdir(os.path.join(path, ".git")):
        subprocess.run(["git", "init"], cwd=path, check=True)


def main():
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    ensure_git_repo(WORKSPACE_DIR)

    logger = MCPLogger()

    print("Levantando servidores MCP...")
    manager = build_mcp_manager(logger)
    print(f"Herramientas disponibles: {[t['name'] for t in manager.get_all_tools()]}")

    bot = Chatbot(mcp_manager=manager)

    try:
        run(bot=bot, logger=logger)
    finally:
        manager.close_all()


if __name__ == "__main__":
    main()