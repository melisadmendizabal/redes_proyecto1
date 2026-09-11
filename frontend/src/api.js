// Capa mínima para hablar con el backend de Python (interfaces/web.py).
// Gracias al proxy de Vite, basta con rutas relativas a /api.

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`/api${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error(
      "No se pudo conectar con el servidor. ¿Está corriendo `python -m main_web`?"
    );
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Error ${res.status}`);
  return data;
}

export const getStatus = () => request("/status");
export const getCatalog = () => request("/catalog");
export const getHistory = () => request("/history");
export const getLog = (since = 0) => request(`/log?since=${since}`);
export const resetChat = () => request("/reset", { method: "POST" });
export const sendMessage = (message) =>
  request("/chat", { method: "POST", body: JSON.stringify({ message }) });
