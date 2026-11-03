import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    // Lokal ishlaganda API so'rovlari Django'ga (manage.py runserver) yo'naltiriladi
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
