// Icon gallery offered when creating/editing a profile (/admin/profiles).
// `profiles.icon` stores the slug of an SVG in src/images/icons/ — the same
// convention as `modules.icon` / `options.icon` — so any surface can render it
// with `iconSvg(slug)`. Each entry's label is `profile_icons.<slug>` in i18n.

const icons = import.meta.glob("/src/images/icons/*.svg", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

/** Raw SVG markup for an icon slug, or "" when there is no such file. */
export function iconSvg(slug: string | null | undefined): string {
  if (!slug) return "";
  return icons[`/src/images/icons/${slug}.svg`] ?? "";
}

/** Typical organizational roles, in gallery order. All are people icons (a
 * person with a role badge; Tabler Icons, MIT), stored as `person-*.svg`. */
export const PROFILE_ICON_SLUGS = [
  "person-shield",    // Administrator
  "person-cog",       // Operations
  "person-star",      // Leader / manager
  "person-group",     // Team
  "person-users",     // Collaborator
  "person-check",     // Approver
  "person-search",    // Reviewer
  "person-scan",      // Auditor
  "person-code",      // Developer
  "person-bolt",      // Data / AI specialist
  "person-edit",      // Content editor
  "person-share",     // Marketing / communications
  "person-dollar",    // Finance
  "person-heart",     // Human resources
  "person-plus",      // Recruiter
  "person-question",  // Support
  "person-screen",    // Trainer
  "person-pin",       // Field staff
  "person-square",    // Guest / external
  "person-circle",    // Generic user
] as const;

export interface IconOption {
  value: string;
  label: string;
  svg: string;
}

export const PROFILE_ICON_OPTIONS: IconOption[] = PROFILE_ICON_SLUGS.map((slug) => ({
  value: slug,
  label: `profile_icons.${slug}`,
  svg: iconSvg(slug),
}));
