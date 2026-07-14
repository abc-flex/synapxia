/**
 * assetSections — a category-agnostic superset of the per-catalog `DetailSection`
 * configs (defined inline in PromptDetailModal / McpDetailModal / AgentDetailModal).
 *
 * Used by the /lib/assets edit modal's read-only "Versions" tab, which spans all
 * categories and so has no single per-category section list. `renderCharacterizationSections`
 * skips any section whose value is empty (the `if (el)` guard in catalogDetail.ts),
 * so passing the superset renders exactly the features a given version actually has.
 *
 * Labels use the generic `features.<CODE>` i18n namespace. Rich fields read the
 * `detail` column; short fields read `value` — matching the seed/write convention
 * (see memory: PLATFORM/MODE/MODEL/TEMP/OVERVIEW → value; the rest → detail).
 */
import type { DetailSection } from "@/lib/catalogDetail";

export const ALL_DETAIL_SECTIONS: DetailSection[] = [
  { type: "block", labelKey: "features.OVERVIEW", feature: "OVERVIEW" },
  { type: "inline", labelKey: "features.PLATFORM", feature: "PLATFORM" },
  { type: "inline", labelKey: "features.MODE", feature: "MODE" },
  { type: "inline", labelKey: "features.SUGGESTED_MODEL", feature: "SUGGESTED_MODEL" },
  { type: "inline", labelKey: "features.SUGGESTED_TEMPERATURE", feature: "SUGGESTED_TEMPERATURE" },
  { type: "code", labelKey: "features.PROMPT_TEMPLATE", feature: "PROMPT_TEMPLATE", column: "detail" },
  { type: "block", labelKey: "features.EXAMPLE_OUTPUT", feature: "EXAMPLE_OUTPUT", column: "detail" },
  { type: "tools", labelKey: "features.TOOLS", feature: "TOOLS", column: "detail" },
  { type: "block", labelKey: "features.CONTENT", feature: "CONTENT", column: "detail" },
  { type: "code", labelKey: "features.SERVER_CONFIG", feature: "SERVER_CONFIG", column: "detail" },
  { type: "code", labelKey: "features.INSTRUCTIONS", feature: "INSTRUCTIONS", column: "detail" },
];
