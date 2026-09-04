/**
 * assetSections — a category-agnostic superset of every LIB category's
 * `DetailSection` configs (one section per feature across PROMPTS/MCPS/AGENTS/…).
 *
 * Used by the /lib/assets edit modal's read-only "Versions" tab, which spans all
 * categories and so has no single per-category section list. `renderCharacterizationSections`
 * skips any section whose value is empty (the `if (el)` guard in catalogDetail.ts),
 * so passing the superset renders exactly the features a given version actually has.
 *
 * Labels use the generic `features.<CODE>` i18n namespace. Every section reads the
 * `value` column (the default `DetailSection.column`) — `value` is the field's full
 * payload for every feature (short or rich alike; e.g. TOOLS' array, SERVER_CONFIG's
 * JSON, INSTRUCTIONS' full text). `detail` is a separate, optional, user-entered
 * elaboration (the Show/Hide "detail" toggle on the create/edit + propose forms) —
 * it is NOT an alternate/richer copy of `value` and must never be read as if it were.
 */
import type { DetailSection } from "@/lib/catalogDetail";

export const ALL_DETAIL_SECTIONS: DetailSection[] = [
  { type: "block", labelKey: "features.OVERVIEW", feature: "OVERVIEW" },
  { type: "inline", labelKey: "features.PLATFORM", feature: "PLATFORM" },
  { type: "inline", labelKey: "features.MODE", feature: "MODE" },
  { type: "inline", labelKey: "features.SUGGESTED_MODEL", feature: "SUGGESTED_MODEL" },
  { type: "inline", labelKey: "features.SUGGESTED_TEMPERATURE", feature: "SUGGESTED_TEMPERATURE" },
  { type: "code", labelKey: "features.PROMPT_TEMPLATE", feature: "PROMPT_TEMPLATE" },
  { type: "block", labelKey: "features.EXAMPLE_OUTPUT", feature: "EXAMPLE_OUTPUT" },
  { type: "tools", labelKey: "features.TOOLS", feature: "TOOLS" },
  { type: "block", labelKey: "features.CONTENT", feature: "CONTENT" },
  { type: "code", labelKey: "features.SERVER_CONFIG", feature: "SERVER_CONFIG" },
  { type: "code", labelKey: "features.INSTRUCTIONS", feature: "INSTRUCTIONS" },
];
