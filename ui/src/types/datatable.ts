// Shared types for the DataTable component family (components/table/).
// Extend-only: never rename existing keys (API/contract stability).

export type ColumnAs =
  | "title"
  | "status"
  | "tags"
  | "date"
  | "badge"
  | "boolean"
  | "text";

/**
 * Column config schema:
 *   title   → bold name + optional muted subtitle line (subtitleKey/subtitleFormat)
 *   status  → semantic colored pill (statusTone)
 *   tags    → comma-split gray chips
 *   date    → locale-formatted date (dateFormat: "date" | "relative")
 *   badge   → single gray chip
 *   boolean → check icon when truthy (implicit fallback kept for unflagged columns)
 *   text    → raw value (default)
 */
export interface ColumnConfig {
  key: string;
  label: string;
  /** false → kept in data/export context but no <th>/<td>. */
  visible?: boolean;
  as?: ColumnAs;
  /** ONLY for as:"title" — field used for the muted second line. */
  subtitleKey?: string;
  subtitleFormat?: "relative" | "text" | "date";
  /** ONLY for as:"date" — defaults to "date". */
  dateFormat?: "date" | "relative";
}

/** Option shape accepted by the toolbar filter <select>s. */
export interface FilterOption {
  value?: string;
  code?: string;
  label?: string;
  name?: string;
  /** Runtime i18n key for the option label (used by the 3rd filter). */
  i18n?: string;
}

/** A configured column filter (one <select>). */
export interface FilterConfig {
  id: string;
  key: string | null;
  options: FilterOption[];
  defaultValue: string;
  /** i18n key for the empty "all" option; falls back to `${key}_modal.filter_title`. */
  allLabel?: string | null;
}
