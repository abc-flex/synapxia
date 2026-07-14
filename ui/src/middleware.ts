/**
 * Astro middleware — server-side auth gate + SSR token plumbing.
 *
 * The access token rides in an HTTP-only cookie `auth_token` set by the
 * API at login. The browser auto-attaches it (same-origin thanks to the
 * Vite proxy / Vercel rewrite). The Astro server can read it via
 * `context.cookies`, so:
 *   1. We redirect unauthenticated requests to /login here, server-side
 *      (no more inline-script bouncing → no flash of empty content).
 *   2. We stash the token in AsyncLocalStorage so api.ts can forward it
 *      as a Bearer header when SSR code calls the API.
 */

import { defineMiddleware } from "astro:middleware";
import { ssrContext } from "@/lib/api";

const PUBLIC_ROUTES = ["/login", "/signup", "/", "/index"];

export const onRequest = defineMiddleware((ctx, next) => {
  const token = ctx.cookies.get("auth_token")?.value;
  const path = ctx.url.pathname;
  const isAuthScreen = path === "/login" || path === "/signup";
  const isPublic = PUBLIC_ROUTES.includes(path);

  // Don't auth-gate the API proxy itself or Astro asset routes.
  if (path.startsWith("/api/") || path.startsWith("/_") || path.includes(".")) {
    return next();
  }

  if (!token && !isPublic) {
    return ctx.redirect("/login");
  }
  if (token && isAuthScreen) {
    return ctx.redirect("/");
  }

  // Run the request inside ALS so apiGet (called from page frontmatters)
  // can find the token and forward it to the API.
  return ssrContext.run({ token }, () => next());
});
