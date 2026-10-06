/**
 * Shared table-export helpers, extracted from components/table/advancedTable.ts
 * so DataTable and the Usage Metrics tables (specs/008-usage-metrics) export
 * the same way. Output for values without double quotes is unchanged from the
 * original DataTable export; embedded quotes are now doubled (RFC 4180).
 */

export interface ExportColumn {
  key: string;
  label: string;
}

const cell = (value: unknown): string => `"${String(value ?? "").replace(/"/g, '""')}"`;

/** Quoted CSV. `bom: true` prefixes a UTF-8 BOM so Excel reads accents correctly. */
export function toCSV(
  data: Record<string, any>[],
  columns: ExportColumn[],
  opts: { bom?: boolean } = {},
): string {
  const header = columns.map((c) => cell(c.label)).join(",");
  const rows = data.map((row) => columns.map((c) => cell(row[c.key])).join(","));
  return (opts.bom ? "﻿" : "") + [header, ...rows].join("\n");
}

export function downloadFile(content: string | Blob, filename: string, type: string): void {
  const blob = content instanceof Blob ? content : new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** e.g. `usage-dashboards_2026-09-06_2026-10-05_unit-ENG` (no extension). */
export function exportFileName(
  table: string,
  period: { date_from: string; date_to: string },
  filter: { unit?: string | null; team?: string | null } = {},
): string {
  const parts = [table, period.date_from, period.date_to];
  if (filter.unit) parts.push(`unit-${filter.unit}`);
  if (filter.team) parts.push(`team-${filter.team === "__none__" ? "none" : filter.team}`);
  return parts.join("_").replace(/[^\w.-]+/g, "-");
}
