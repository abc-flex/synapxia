import { defineConfig } from "astro/config";
import tailwind from "@astrojs/tailwind";
import { fileURLToPath } from "node:url";

export default defineConfig({
  site: "http://localhost:4321",
  integrations: [tailwind()],
  vite: {
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      watch: {
        usePolling: true,
        interval: 300,
      },
    },
  },
});
