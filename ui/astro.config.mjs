import { defineConfig } from "astro/config";
import tailwind from "@astrojs/tailwind";
import vercel from "@astrojs/vercel/serverless";
import { fileURLToPath } from "node:url";
import dns from "node:dns";

// Force IPv4 first — http-proxy (used by Vite's server.proxy) otherwise
// tries IPv6 and the API container only listens on IPv4 in the Docker
// bridge network, causing ECONNREFUSED.
dns.setDefaultResultOrder("ipv4first");

export default defineConfig({
  site: process.env.SITE_URL || "http://localhost:4321",
  // Per-request SSR so middleware sees real cookies/headers. Pages opt-in
  // to prerendering with `export const prerender = true` (e.g. /login).
  output: "server",
  adapter: vercel(),
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
      // Dev: proxy /api/* to the API container so the browser sees ONE
      // origin (localhost:4321). The cookie set by the API gets rewritten
      // to localhost:4321 and is then visible to both the browser and to
      // the Astro server (via context.cookies).
      proxy: {
        "/api": {
          // Always target the API container hostname. Do NOT honor
          // PUBLIC_API_BASE_URL here — that env var is set in
          // .env.development to http://localhost:8000 (a host-side URL),
          // which resolves to the UI container itself when used as a
          // proxy target inside Docker. The PROXY_API_TARGET env var
          // exists as an explicit override for non-Docker dev setups.
          target: process.env.PROXY_API_TARGET || "http://synapxia-api:80",
          changeOrigin: true,
          cookieDomainRewrite: "",
          // FastAPI's trailing-slash redirect emits an absolute Location
          // header (`http://synapxia-api:80/...`) that the browser can't
          // resolve. autoRewrite rewrites the host:port back to the
          // proxy's origin (localhost:4321) so the browser follows the
          // 307 same-origin and the auth cookie attaches.
          autoRewrite: true,
          protocolRewrite: "http",
          // Forward X-Forwarded-For/Host/Proto so the API can build
          // correct absolute URLs itself once uvicorn runs with
          // --proxy-headers (Layer 2). autoRewrite stays as a safety net.
          xfwd: true,
          configure: (proxy) => {
            proxy.on("error", (err, req) => {
              console.error(
                `[vite proxy] /api → API error: ${err.message} (url=${req.url})`,
              );
            });
          },
        },
      },
    },
  },
});
