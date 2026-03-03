// src/utils/getLocale.ts
import type { Locale } from "@/i18n";
import type { APIContext } from "astro";

export const getLocale = (context: APIContext): Locale => {
  // For static sites, default to English
  // The actual language will be determined client-side via localStorage
  return "en" as Locale;
}
