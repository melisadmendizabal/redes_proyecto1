import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// El proxy manda todo lo que empiece con /api al backend de Python
// (python -m main_web). Si cambias WEB_PORT en el backend, cámbialo aquí.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:5050",
    },
  },
});
