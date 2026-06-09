/**
 * Astro middleware — auth gate is NOT here.
 *
 * The access token lives in localStorage (browser-only). The Astro server
 * cannot read localStorage, so a server-side gate that calls `getToken()`
 * always sees "no token" and bounces every navigation to /login.
 *
 * Auth is therefore enforced CLIENT-SIDE via the synchronous `<script is:inline>`
 * gate at the top of `src/layouts/BaseLayout.astro` and `src/layouts/Layout.astro`.
 *
 * Keeping this file as a pass-through so the wiring is preserved for a
 * future cookie-based migration (HTTP-only cookies are readable server-side
 * via `context.cookies` and would let us re-enable a server gate here).
 */

import { defineMiddleware } from 'astro:middleware';

export const onRequest = defineMiddleware((_, next) => next());
