import gbFlag from '@/images/flags/gb.svg?raw';
import coFlag from '@/images/flags/co.svg?raw';

/**
 * Inline SVG flags keyed by ISO 3166-1 alpha-2 country code.
 *
 * Unicode flag emoji (🇬🇧, 🇨🇴) don't render as pictures on Windows — the
 * OS has no color glyphs for the regional-indicator sequences, so browsers
 * fall back to showing the two letters as plain text ("GB", "CO"). Rendering
 * an actual SVG sidesteps the OS font entirely and looks the same everywhere.
 */
export const FLAG_ICONS: Record<string, string> = {
  gb: gbFlag,
  co: coFlag,
};
