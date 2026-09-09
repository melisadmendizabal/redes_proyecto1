# Imagen ligera de Python para el servidor remoto de farmacia (HTTP).
FROM python:3.11-slim

WORKDIR /app

# Solo las dependencias que necesita ESTE servidor (no todo el proyecto).
COPY servers/pharmacy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos solo el paquete servers/ (con su lógica y el adaptador HTTP).
COPY servers/ ./servers/

# Cloud Run inyecta la variable de entorno PORT; remote_http.py ya la lee.
# ENV PORT=8080
EXPOSE 10000

# Servidor de producción (gunicorn), no el servidor de desarrollo de Flask.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 servers.pharmacy.remote_http:app"]