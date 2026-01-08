// src/utils/getLocale.ts
import type { APIContext } from "astro";

export function getLocale(context: APIContext) {
  // Check for language cookie first
  const cookies = context.cookies;
  const langCookie = cookies.get("lang")?.value;
  
  if (langCookie === "es" || langCookie === "en") {
    return langCookie;
  }

  // Fallback to accept-language header
  const lang = context.request.headers
    .get("accept-language")
    ?.split(",")[0]
    ?.split("-")[0];

  if (lang === "es") return lang;
  return "en";
}
