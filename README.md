# Redes Proyecto 1 — MCP Chatbot

A chatbot (MCP host) that connects to multiple MCP (Model Context Protocol) servers using a hand-written JSON-RPC 2.0 client, **no MCP SDKs involved**. It can be used from the terminal or from a web interface.

Repository: https://github.com/melisadmendizabal/redes_proyecto1

Author: Melisa Mendizabal (23778) — CC3067 Redes, Universidad del Valle de Guatemala.

## Project description

This project implements the MCP host/client side manually, following the JSON-RPC 2.0 spec and the MCP lifecycle (`initialize` → `notifications/initialized` → `tools/list` → `tools/call`) over two transports:

- **stdio** for the local servers (Filesystem, Git and the local Pharmacy server).
- **Streamable HTTP** (simplified) for the remote Pharmacy server, deployed on Render.

The chatbot connects to three MCP servers at once and lets the LLM (Google Gemini) decide which tool to use via function calling. The LLM client, the MCP client and the interfaces are independent layers, so the interface can be swapped without touching the core.

## Implemented features

| # | Feature | Status |
|---|---|---|
| 1 | Connection to an LLM via its API (Google Gemini) | ✅ |
| 2 | Context maintained across a conversation session | ✅ |
| 3 | Log of all MCP requests/responses (`/log` in the CLI, side panel in the web UI) | ✅ |
| 4 | Official local MCP servers: Filesystem + Git | ✅ |
| 5 | Custom local MCP server (Pharmacy use case, stdio) | ✅ |
| 6 | Remote version of the custom MCP server (HTTP, deployed on Render) | ✅ |
| 7 | Wireshark traffic analysis (JSON-RPC classification + OSI layers) | ✅ (see the final report) |
| Extra | Web user interface (React + Flask API) | ✅ |

## Architecture

```
core/               LLM client, chatbot logic, MCP clients (stdio + HTTP), MCP manager, logger
interfaces/         Thin wrappers with no business logic: cli.py (terminal) and web.py (Flask API)
servers/pharmacy/   Custom MCP server: logic.py (catalog + tools), local_stdio.py, remote_http.py
frontend/           React + Vite web interface
main.py             Wires everything together (which servers to launch) and starts the CLI
main_web.py         Same wiring, but starts the HTTP API consumed by the frontend
Dockerfile          Image for the remote Pharmacy server (gunicorn)
```

The core layer knows nothing about the terminal or the browser, so both interfaces reuse `core/chatbot.py` unchanged.

## Requirements

- Python 3.11+
- Node.js + npm (for the official Filesystem MCP server, launched via `npx`, and for the web frontend)
- Git installed and available in PATH

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/melisadmendizabal/redes_proyecto1
   cd redes_proyecto1
   ```
2. Install the Python dependencies:
   ```
   pip install requests python-dotenv mcp-server-git flask
   ```
3. Create a `.env` file in the project root with your own Gemini API key:
   ```
   GEMINI_API_KEY=your_key_here
   ```
   Get a free key at https://aistudio.google.com. Note: the free tier has a daily request quota that resets at midnight Pacific Time.

### Optional environment variables

| Variable | Purpose |
|---|---|
| `PHARMACY_REMOTE_URL` | If set (e.g. `https://redes-proyecto1-9ubr.onrender.com`), the chatbot uses the **remote** Pharmacy server over HTTP instead of the local stdio one. |
| `WEB_PORT` | Port of the web API (default `5050`). If you change it, also update the proxy in `frontend/vite.config.js`. |
| `SSLKEYLOGFILE` | If set, the HTTP client dumps the TLS session keys to that file so Wireshark can decrypt the HTTPS traffic (see [Wireshark analysis](#wireshark-analysis)). |

## Usage

### Terminal interface

Run the whole system (chatbot + all MCP servers) from the project root:

```
python -m main
```

This will:
1. Create a `workspace/` folder (used by both the Filesystem and Git servers) and initialize it as a git repository if it isn't one yet.
2. Launch the Filesystem and Git MCP servers as subprocesses, and connect to the Pharmacy server (local subprocess, or remote if `PHARMACY_REMOTE_URL` is set).
3. Start an interactive chat loop in the terminal.

Commands inside the chat:

- `/reset` — clears the conversation context
- `/log` — shows all MCP requests/responses exchanged so far
- `/salir` — exits the program

### Web interface

You need two terminals.

**Terminal 1** — backend (project root):

```
python -m main_web
```

**Terminal 2** — frontend:

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

*Optional for a demo:* run `npm run build` inside `frontend/`; then `python -m main_web` alone is enough and the UI is served at http://localhost:5050 (no Vite needed).

What the interface includes:

- Chat with session context, Markdown answers and **chips** showing which MCP tool the LLM used in each reply.
- Pharmacy catalog with price and stock bar; it refreshes automatically after a purchase.
- Connected MCP servers (filesystem, git, pharmacy) with their tools and a `local · stdio` or `remote · HTTP` label.
- **MCP log** side panel: live requests, responses and notifications, filterable by server, with the full JSON-RPC message when an entry is expanded.
- Connection status, "new conversation" button (equivalent to `/reset`) and a responsive layout.
- The history survives a page reload because the context lives on the server.

Notes: the Nunito font is loaded from Google Fonts (falls back to Segoe UI offline). The catalog calls `list_medications` directly without going through Gemini, so it does not spend LLM quota, but those calls also appear in the MCP log.

Backend API (`interfaces/web.py`):

| Method | Route | Description |
|---|---|---|
| GET | `/api/status` | Connected MCP servers, their tools and the LLM model |
| GET | `/api/catalog` | Pharmacy catalog (via the `list_medications` tool) |
| GET | `/api/history` | Messages of the current conversation |
| POST | `/api/chat` | `{"message": "..."}` → `{"reply": "...", "tool_calls": [...]}` |
| POST | `/api/reset` | Clears the conversation context |
| GET | `/api/log` | MCP log (`?since=N` to fetch only new entries) |

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

Simulates a pharmacy chain chatbot: recommends medications based on symptoms and lets the user purchase them, with an in-memory stock catalog. Tools: `search_by_symptom`, `get_medication_info`, `list_medications`, `purchase_medication`. The full specification (parameters, examples, error codes) is in the final report (`Reporte_Final_Proyecto1.docx`).

The business logic lives in `servers/pharmacy/logic.py` and is shared by both transports.

### Local version (stdio)

Run it standalone (for testing, without the rest of the chatbot):

```
python -m servers.pharmacy.local_stdio
```

### Remote version (HTTP)

Same tools, exposed through a single endpoint `POST /mcp` (one JSON-RPC message per request, session tracked with the `Mcp-Session-Id` header) plus `GET /health`. Deployed on Render:

```
https://redes-proyecto1-9ubr.onrender.com
```

Run it locally:

```
pip install -r servers/pharmacy/requirements.txt
gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 4 servers.pharmacy.remote_http:app
```

Or with Docker:

```
docker build -t pharmacy-mcp .
docker run -p 10000:10000 pharmacy-mcp
```

To make the chatbot use it, add `PHARMACY_REMOTE_URL=<url>` to your `.env`. The chatbot does not distinguish between the local and the remote server: both expose the same interface through `core/mcp_manager.py`.

> Render's free tier puts the service to sleep after inactivity, so the first request can take a while.

## Wireshark analysis

The remote server is served over HTTPS (TLS 1.3), so a plain capture only shows encrypted TLS records. To decrypt the MCP messages:

1. Set the key log file **before** starting the chatbot, e.g. on Windows PowerShell:
   ```
   $env:SSLKEYLOGFILE = "C:\ruta\sslkeys.log"
   $env:PHARMACY_REMOTE_URL = "https://redes-proyecto1-9ubr.onrender.com"
   python -m main
   ```
2. Start a Wireshark capture on the active interface with the display filter `tcp.port == 443` (or filter by the server IP).
3. In Wireshark: *Edit → Preferences → Protocols → TLS → (Pre)-Master-Secret log filename* and select the same `sslkeys.log`.
4. Use `Follow → TCP Stream` / `Follow → HTTP Stream` to read the JSON-RPC messages (`initialize`, `notifications/initialized`, `tools/list`, `tools/call`).

The `.pcap`/`.pcapng` and `.log` files are excluded from the repository through `.gitignore`, because the key log file would allow anyone holding the capture to read the traffic. The classification of every message (synchronization / request / response) and the analysis by OSI layers are documented in the final report.

## Known limitations (documented for transparency)

- The pharmacy catalog is in-memory only; it resets every time the server restarts.
- Google Gemini's free tier is rate-limited (requests per minute and per day); the LLM client retries automatically on 429/503 errors, but very frequent testing can still exhaust the daily quota.
- The remote server implements a simplified Streamable HTTP transport: it answers every request with a plain JSON body (no SSE streaming) and does not implement session deletion (`DELETE`).
- Both interfaces are single-user (one conversation session).
- Pharmacy recommendations are illustrative and do not replace medical advice.
