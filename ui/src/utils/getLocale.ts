// src/utils/getLocale.ts
import type { APIContext } from "astro";

export function getLocale(context: APIContext) {
  const lang = context.request.headers
    .get("accept-language")
    ?.split(",")[0]
    ?.split("-")[0];

  if (lang === "fr" || lang === "es") return lang;
  return "en";
}
