"""
core/llm_client.py

Encapsula la comunicación con la API de Gemini (Google) a nivel HTTP.
No sabe nada de terminal, MCP, ni UI: solo manda contenido y regresa la
respuesta del modelo.

OJO: el formato de Gemini es distinto al de Anthropic:
  - Los mensajes se llaman "contents" (no "messages").
  - Los roles son "user" y "model" (no "user" y "assistant").
  - Cada mensaje tiene una lista "parts", cada parte con un campo "text".
Esto afecta directamente cómo chatbot.py arma el historial (ver Session
en ese archivo).
"""

import os
import requests
from dotenv import load_dotenv

# Carga las variables definidas en tu archivo .env (en la raíz del
# proyecto) hacia el entorno del proceso. Sin esto, crear el .env no
# sirve de nada: Python no lo lee solo.
load_dotenv()

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Modelo por defecto. Revisa en https://aistudio.google.com qué modelos
# están habilitados para tu API key gratuita (la disponibilidad de
# modelos en el free tier cambia con el tiempo).
DEFAULT_MODEL = "gemini-3.6-flash"
DEFAULT_MAX_OUTPUT_TOKENS = 1024


class LLMClientError(Exception):
    """Error al comunicarse con la API de Gemini."""
    pass


class LLMClient:
    def __init__(self, api_key: str = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise LLMClientError(
                "No se encontró la API key. Define la variable de entorno "
                "GEMINI_API_KEY (por ejemplo en un archivo .env que NO "
                "subas a git)."
            )
        self.model = model

    def send_message(
        self,
        contents: list[dict],
        system_instruction: str = None,
        tools: list[dict] = None,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    ) -> dict:
        """
        Manda la conversación completa a Gemini y regresa el JSON crudo
        de la respuesta.

        contents: lista de dicts tipo:
            [{"role": "user", "parts": [{"text": "Hola"}]},
             {"role": "model", "parts": [{"text": "..."}]},
             {"role": "user", "parts": [{"text": "..."}]}]
            Este historial lo arma chatbot.py; este cliente no guarda
            estado entre llamadas (la API es stateless).

        system_instruction: instrucciones de sistema (opcional).

        tools: definición de herramientas en formato Gemini (opcional,
            lo usarás cuando conectes los servidores MCP: cada tool de
            MCP se traduce a un "functionDeclaration" de Gemini).
        """
        url = f"{GEMINI_API_BASE}/{self.model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_output_tokens},
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
        except requests.RequestException as e:
            raise LLMClientError(f"Fallo de red al llamar a la API: {e}")

        if response.status_code != 200:
            raise LLMClientError(
                f"La API respondió con error {response.status_code}: "
                f"{response.text}"
            )

        return response.json()

    def get_text_response(self, contents: list[dict], **kwargs) -> str:
        """
        Atajo para cuando solo te interesa el texto de la respuesta.
        Toma el primer candidate y concatena sus partes de texto.
        """
        data = self.send_message(contents, **kwargs)

        try:
            candidate = data["candidates"][0]
            parts = candidate["content"]["parts"]
        except (KeyError, IndexError):
            raise LLMClientError(f"Respuesta inesperada de Gemini: {data}")

        text_parts = [p["text"] for p in parts if "text" in p]
        return "\n".join(text_parts)


# --- Prueba rápida manual ---
if __name__ == "__main__":
    client = LLMClient()
    historial = [{"role": "user", "parts": [{"text": "¿Quién fue Alan Turing?"}]}]
    respuesta = client.get_text_response(historial)
    print(respuesta)