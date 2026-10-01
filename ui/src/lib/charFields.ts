/**
 * charFields — shared field-definition builder for asset characterization
 * forms (Propose, Modify, asset-detail tabs). One source of truth for:
 *
 *   - ORDER: fields come back in the category's configured `sort_order`
 *     (the specs endpoint sorts server-side; the array order is preserved).
 *   - CONTROL: the input control is derived from the feature —
 *     `select` (feature has a `list` → options from list_items),
 *     `textarea` (long-form features), or `input` (short text).
 *   - REQUIRED: `spec.required` rides along so every form can mark + enforce it.
 *   - Display extras: the feature's name/description and its FEAT_TYPE badge.
 */
import { getSpecificationsbyCategory } from "./specifications";
import { getFeature } from "./features";
import { getListItemsbyList } from "./list_items";
import { labelsByValue, labelsFor, toListOptions } from "./listLang";
import type { Feature, ListItem } from "../types/api";

/** Long-form features rendered as a textarea (single source of truth). */
export const RICH_FEATURES = new Set([
  "PROMPT_TEMPLATE", "EXAMPLE_OUTPUT", "OVERVIEW",
  "CONTENT", "TOOLS", "SERVER_CONFIG", "INSTRUCTIONS",
]);

export type CharControl = "select" | "textarea" | "input";

export interface CharFieldOption {
  value: string;
  label: string;
  /** Every language's label — lets the control follow the language switcher. */
  labels: Record<string, string>;
}

export interface CharFieldDef {
  feature: string;
  /** Feature display name (fallback when there's no i18n key). */
  name: string;
  description?: string;
  /** FEAT_TYPE classification (GENERAL/TECHNICAL/…) — shown as a badge. */
  type?: string;
  /** The FEAT_TYPE value's label in every language (badge text). */
  typeLabels?: Record<string, string>;
  required: boolean;
  control: CharControl;
  /** Select options (empty unless control === "select"). */
  options: CharFieldOption[];
  defaultValue: string;
}

const featureCache = new Map<string, Feature>();
const listItemsCache = new Map<string, ListItem[]>();

async function listItems(code: string): Promise<ListItem[]> {
  let items = listItemsCache.get(code);
  if (!items) {
    try {
      items = await getListItemsbyList(code, 0, 1000);
      listItemsCache.set(code, items);
    } catch {
      items = [];
    }
  }
  return items;
}

/**
 * Build the ordered field definitions for a category's characterization form.
 * Feature/list lookups are cached per session; a failed lookup degrades to a
 * plain text control instead of dropping the field.
 */
export async function buildCharFieldDefs(category: string): Promise<CharFieldDef[]> {
  const [specs, featTypes] = await Promise.all([
    getSpecificationsbyCategory(category, 0, 1000),
    listItems("FEAT_TYPE").then(labelsByValue),
  ]);
  return Promise.all(
    specs.map(async (spec) => {
      let feature = featureCache.get(spec.feature);
      if (!feature) {
        try {
          feature = await getFeature(spec.feature);
          featureCache.set(spec.feature, feature);
        } catch {
          feature = { code: spec.feature, name: spec.feature } as Feature;
        }
      }

      let options: CharFieldOption[] = [];
      if (feature.list) {
        options = toListOptions(await listItems(feature.list));
      }

      const control: CharControl = options.length
        ? "select"
        : RICH_FEATURES.has(spec.feature)
          ? "textarea"
          : "input";

      return {
        feature: spec.feature,
        name: feature.name || spec.feature,
        description: feature.description || undefined,
        type: feature.type || undefined,
        typeLabels: feature.type ? labelsFor(featTypes, feature.type) : undefined,
        required: !!spec.required,
        control,
        options,
        defaultValue: spec.default_value ?? "",
      };
    }),
  );
}
