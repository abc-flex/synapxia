// src/utils/getLocale.ts
import type { APIContext } from "astro";

export const getLocale = (context: APIContext) => {
  // For static sites, default to English
  // The actual language will be determined client-side via localStorage
  return "en";
}
