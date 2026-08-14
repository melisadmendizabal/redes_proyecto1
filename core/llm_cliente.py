
# Encapsula la comunicación con la API de Anthropic (Claude) a nivel HTTP.
# No sabe nada de terminal, MCP, ni UI: solo manda mensajes y regresa la
# respuesta del modelo. Esto es lo que la interfaz (CLI o Web) y el resto
# del chatbot van a usar.


import os
import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# Modelo por defecto. claude-sonnet-5 da buena calidad; si te preocupan
# los créditos gratuitos, puedes cambiarlo a claude-haiku-4-5-20251001
# (más barato) mientras desarrollas y pruebas.
DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_MAX_TOKENS = 1024


class LLMClientError(Exception):
    #Error al comunicarse con la API de Anthropic.
    pass


class LLMClient:
    def __init__(self, api_key: str = None, model: str = DEFAULT_MODEL):
        # Nunca hardcodees la API key. Se lee de una variable de entorno.
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise LLMClientError(
                "No se encontró la API key. Define la variable de entorno "
                "ANTHROPIC_API_KEY (por ejemplo en un archivo .env que NO "
                "subas a git)."
            )
        self.model = model

    def send_message(
        self,
        messages: list[dict],
        system: str = None,
        tools: list[dict] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> dict:
       
        # Manda una lista de mensajes a la API y regresa la respuesta cruda
        # (el dict completo que devuelve la API).

        # messages: lista de dicts tipo:
        #     [{"role": "user", "content": "Hola"},
        #      {"role": "assistant", "content": "..."},
        #      {"role": "user", "content": "..."}]
        #     Este historial es responsabilidad de quien llama (chatbot.py):
        #     este cliente no guarda estado entre llamadas.

        # system: instrucciones de sistema (opcional).

        # tools: lista de herramientas en formato Anthropic (opcional). Esto
        #     lo vas a usar más adelante para conectar los servidores MCP:
        #     conviertes cada "tool" que expone un servidor MCP a este
        #     formato, y si el modelo decide usar una, te lo indica en la
        #     respuesta (content con type "tool_use").

        # Regresa el JSON completo de la respuesta (no solo el texto), para
        # que quien llama pueda revisar stop_reason, uso de tokens, y bloques
        # de tipo tool_use si los hay.
     
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(
                ANTHROPIC_API_URL, headers=headers, json=payload, timeout=60
            )
        except requests.RequestException as e:
            raise LLMClientError(f"Fallo de red al llamar a la API: {e}")

        if response.status_code != 200:
            raise LLMClientError(
                f"La API respondió con error {response.status_code}: "
                f"{response.text}"
            )

        return response.json()

    def get_text_response(self, messages: list[dict], **kwargs) -> str:

        # Atajo para cuando solo te interesa el texto de la respuesta
        # (sin tool use). Concatena todos los bloques de tipo "text".

        data = self.send_message(messages, **kwargs)
        text_blocks = [
            block["text"] for block in data.get("content", [])
            if block.get("type") == "text"
        ]
        return "\n".join(text_blocks)


#Prueba
if __name__ == "__main__":
    client = LLMClient()
    historial = [{"role": "user", "content": "¿Quién fue Alan Turing?"}]
    respuesta = client.get_text_response(historial)
    print(respuesta)