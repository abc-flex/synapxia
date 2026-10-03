/**
 * Grant recipients for the per-resource Permissions tabs (initiatives,
 * dashboards): the options for each TARGET_TYPE and a label for a stored
 * (target_type, target_code) pair. PUBLIC grants store target_code "ALL".
 *
 * Options are cached per page load — users, roles, teams, units and projects
 * do not change while a dialog is open.
 */
import { getUsersSelect } from "./users";
import { getRolesSelect } from "./roles";
import { getTeamsSelect } from "./teams";
import { getBusinessUnitsSelect } from "./business_units";
import { getProjectsSelect } from "./projects";

export type SelectOption = { value: string; label: string };

/** What PermissionsTab.svelte needs from a resource's grant API. */
export interface PermissionsApi {
  list: (resourceId: number) => Promise<any[]>;
  create: (resourceId: number, body: {
    target_type: string; target_code: string; access_level: string;
    valid_from?: string | null; valid_to?: string | null;
  }) => Promise<{ id: number }>;
  revoke: (grantId: number) => Promise<any>;
}

export const PUBLIC_TARGET = "PUBLIC";
export const PUBLIC_CODE = "ALL";

const LOADERS: Record<string, () => Promise<SelectOption[]>> = {
  USER: getUsersSelect,
  ROLE: getRolesSelect,
  TEAM: getTeamsSelect,
  UNIT: getBusinessUnitsSelect,
  PROJECT: getProjectsSelect,
};

const cache = new Map<string, Promise<SelectOption[]>>();

/** The recipients a grant of `targetType` can name (empty for PUBLIC/unknown). */
export function targetOptions(targetType: string): Promise<SelectOption[]> {
  const loader = LOADERS[targetType];
  if (!loader) return Promise.resolve([]);
  let pending = cache.get(targetType);
  if (!pending) {
    pending = loader().catch(() => [] as SelectOption[]);
    cache.set(targetType, pending);
  }
  return pending;
}

/** Display name of a stored recipient; falls back to the raw code. */
export async function resolveTargetLabel(
  targetType: string, targetCode: string, publicLabel = "Public",
): Promise<string> {
  if (targetType === PUBLIC_TARGET) return publicLabel;
  return (await targetOptions(targetType)).find((o) => o.value === targetCode)?.label || targetCode;
}
