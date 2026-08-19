# Redes Proyecto 1 — MCP Chatbot

A terminal chatbot (host) that connects to multiple MCP (Model Context Protocol) servers using a hand-written JSON-RPC 2.0 client, no MCP SDKs involved.

Repository: https://github.com/melisadmendizabal/redes_proyecto1

## Project description

This project implements the MCP host/client side manually, following the JSON-RPC 2.0 spec and the MCP lifecycle (`initialize` → `notifications/initialized` → `tools/list` → `tools/call`) over the **stdio** transport. The chatbot connects to three MCP servers at once and lets the LLM (Google Gemini) decide which tool to use via function calling.

## Implemented features

| # | Feature | Status |
|---|---|---|
| 1 | Connection to an LLM via its API (Google Gemini) | ✅ |
| 2 | Context maintained across a conversation session | ✅ |
| 3 | Log of all MCP requests/responses (viewable with `/log`) | ✅ |
| 4 | Official local MCP servers: Filesystem + Git | ✅ |
| 5 | Custom local MCP server (Pharmacy use case) | ✅ |
| 6 | Remote version of the custom MCP server (Cloud Run) | ⏳ pending |
| 7 | Wireshark traffic analysis | ⏳ pending |

### Architecture

```
core/            LLM client, chatbot logic, MCP client, MCP manager, logger
interfaces/      Thin CLI wrapper (no business logic)
servers/pharmacy/  Custom MCP server (hand-written JSON-RPC over stdio)
main.py          Wires everything together (which servers to launch)
```

The core layer knows nothing about the terminal, so a future Web interface could reuse `core/chatbot.py` without any changes.

## Requirements

- Python 3.11+
- Node.js + npm (for the official Filesystem MCP server, launched via `npx`)
- Git installed and available in PATH

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/melisadmendizabal/redes_proyecto1
   cd redes_proyecto1
   ```
2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
   (or individually: `pip install requests python-dotenv mcp-server-git`)
3. Copy the environment file template and add your own Gemini API key:

   ```
   GEMINI_API_KEY=your_key_here
   ```
   Get a free key at https://aistudio.google.com. Note: the free tier has a daily request quota (currently 20 requests/day per model), which resets at midnight Pacific Time.

## Usage

Run the whole system (chatbot + all MCP servers) from the project root:

```
python -m main
```

This will:
1. Create a `workspace/` folder (used by both the Filesystem and Git servers) and initialize it as a git repository if it isn't one yet.
2. Launch the Filesystem, Git, and Pharmacy MCP servers as subprocesses.
3. Start an interactive chat loop in the terminal.

### Available commands inside the chat

- `/reset` — clears the conversation context
- `/log` — shows all MCP requests/responses exchanged so far
- `/salir` — exits the program

### Example interactions

```
Tú: crea un archivo README.md en el repositorio con el texto "Proyecto MCP - CC3067",
    agrégalo al staging y haz commit con el mensaje "initial commit"
```
```
Tú: tengo dolor de cabeza, ¿qué me recomiendas?
Tú: cómprame 2 de esos
```

## Pharmacy MCP server (custom, industry use case)

Simulates a pharmacy chain chatbot: recommends medications based on symptoms and lets the user purchase them, with an in-memory stock catalog. See `docs/Reporte_Parcial_Proyecto1.docx` for the full specification (tools, parameters, examples).

Run it standalone (for testing, without the rest of the chatbot):
```
python -m servers.pharmacy.local_stdio
```

## Known limitations (documented for transparency)

- The pharmacy catalog is in-memory only; it resets every time main.py restarts.
- Google Gemini's free tier is rate-limited (requests per minute and per day); the LLM client retries automatically on 429/503 errors, but very frequent testing can still exhaust the daily quota.
- The remote (Cloud Run) version of the Pharmacy server and the Wireshark analysis are part of the next delivery, not this one.
