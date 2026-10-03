<script lang="ts">
  /**
   * PermissionsTab — the per-resource Permissions tab shared by Initiative
   * Management (InitiativeDetailTabs) and Dashboard Management
   * (DashboardDetailTabs). Extracted from InitiativeDetailTabs so the grant UI
   * exists once (specs/006-dashboard-management, R11).
   *
   * Grants are staged and persist only when the parent calls `flush()` (the
   * dialogs save one tab at a time). A grant is never deleted: removing a saved
   * row revokes it (the API closes its validity window). As in Asset Management,
   * the tab never shows or asks for dates: a new grant starts now, a revoke ends it now.
   *
   * Every string is read from `${i18nPrefix}.perm_*`, and every control id is
   * `${idPrefix}-perm-*` — the same keys and ids the initiative tab always used.
   */
  import { onMount } from "svelte";
  import { getListItemsbyList } from "@/lib/list_items";
  import { labelsByValue, listLabel, toListOptions } from "@/lib/listLang";
  import {
    PUBLIC_CODE, PUBLIC_TARGET, resolveTargetLabel, targetOptions,
    type PermissionsApi, type SelectOption,
  } from "@/lib/permissionTargets";
  import { getUser } from "@/lib/auth";
  import { translate } from "@/utils/i18nClient";

  type StagedPermission = {
    id?: number;
    targetType: string;
    targetCode: string;
    targetCodeLabel: string;
    access: string;
  };

  let {
    idPrefix,
    api,
    i18nPrefix = "initiative_detail_modal",
    readonly = false,
    onError,
    onRevokeWarning,
  }: {
    idPrefix: string;
    api: PermissionsApi;
    i18nPrefix?: string;
    readonly?: boolean;
    onError?: (msg: string) => void;
    /** Extra confirmation text before revoking a saved grant (null = none). */
    onRevokeWarning?: (grantId: number) => string | null;
  } = $props();

  // ── i18n ──────────────────────────────────────────────────────────────
  let langTick = $state(0);
  const t = (key: string, fallback: string): string => {
    void langTick;
    try {
      const v = translate(`${i18nPrefix}.${key}`);
      if (v && v !== `${i18nPrefix}.${key}`) return v;
    } catch {
      /* non-fatal */
    }
    return fallback;
  };
  const currentLang = (): string =>
    (typeof localStorage !== "undefined" && localStorage.getItem("lang")) === "es" ? "es" : "en";
  let listRaw = $state<Record<string, any[]>>({});
  const listOpts = (code: string): SelectOption[] => {
    void langTick;
    return toListOptions(listRaw[code] ?? [], currentLang());
  };
  const listText = (code: string, value: string | null | undefined): string => {
    void langTick;
    return value ? listLabel(labelsByValue(listRaw[code] ?? []), value, currentLang()) : "";
  };
  // ── State ─────────────────────────────────────────────────────────────
  let resourceId = $state<number | null>(null);
  let staged = $state<StagedPermission[]>([]);
  let initialById = $state(new Map<number, true>());
  const targetTypeOptions = $derived(listOpts("TARGET_TYPE"));
  const accessOptions = $derived(listOpts("ACCESS_LEVEL"));
  let permType = $state("");
  let permCode = $state("");
  let permAccess = $state("");
  let permCodeOptions = $state<SelectOption[]>([]);
  let permCodeDisabled = $state(false);
  let permError = $state("");

  export function dirty(): boolean {
    const stagedIds = new Set(staged.filter((p) => p.id != null).map((p) => p.id));
    for (const [pid] of initialById) if (!stagedIds.has(pid)) return true;
    return staged.some((p) => p.id == null);
  }

  export function count(): number {
    return staged.length;
  }

  /** Saved grant ids still staged (i.e. not marked for revocation). */
  export function liveGrantIds(): number[] {
    return staged.filter((p) => p.id != null).map((p) => p.id as number);
  }

  async function loadLists(): Promise<void> {
    if (listRaw.TARGET_TYPE && listRaw.ACCESS_LEVEL) return;
    const loaded: Record<string, any[]> = {};
    await Promise.all(["TARGET_TYPE", "ACCESS_LEVEL"].map(async (code) => {
      try {
        loaded[code] = await getListItemsbyList(code);
      } catch {
        loaded[code] = [];
      }
    }));
    listRaw = { ...listRaw, ...loaded };
  }

  async function onPermTypeChange(): Promise<void> {
    permCode = "";
    permCodeOptions = [];
    permCodeDisabled = permType === PUBLIC_TARGET;
    if (!permType || permType === PUBLIC_TARGET) return;
    permCodeOptions = await targetOptions(permType);
  }

  function addPermission(): void {
    permError = "";
    if (!permType || !permAccess) {
      permError = t("perm_missing_fields", "Pick a target type, target and access level.");
      return;
    }
    let targetCode: string;
    let targetCodeLabel: string;
    if (permType === PUBLIC_TARGET) {
      targetCode = PUBLIC_CODE;
      targetCodeLabel = t("perm_public", "Public");
    } else {
      targetCode = permCode;
      if (!targetCode) {
        permError = t("perm_missing_fields", "Pick a target type, target and access level.");
        return;
      }
      targetCodeLabel = permCodeOptions.find((o) => o.value === targetCode)?.label || targetCode;
    }
    if (staged.some((p) => p.targetType === permType && p.targetCode === targetCode && p.access === permAccess)) {
      permError = t("perm_duplicate", "This target already has that access.");
      return;
    }
    staged = [
      ...staged,
      { targetType: permType, targetCode, targetCodeLabel, access: permAccess },
    ];
    permType = "";
    permCode = "";
    permCodeOptions = [];
    permAccess = "";
  }

  // Revoking one's own MANAGE grant can lock the caller out — confirm first.
  function removePermission(idx: number): void {
    const p = staged[idx];
    if (p?.id != null) {
      const me = getUser() as { id?: number } | null;
      const isOwnManage =
        p.access === "MANAGE" && p.targetType === "USER" &&
        me && (me.id || me.id === 0) && String(me.id) === p.targetCode;
      if (isOwnManage && !window.confirm(t(
        "perm_self_revoke_confirm",
        "You are about to revoke your own manage access. Continue?",
      ))) return;
      const extra = onRevokeWarning?.(p.id);
      if (extra && !window.confirm(extra)) return;
    }
    staged = staged.filter((_, i) => i !== idx);
  }

  // ── hydrate / flush / reset ───────────────────────────────────────────
  export async function hydrate(id: number): Promise<void> {
    resourceId = id;
    await loadLists();
    let grants: any[] = [];
    try {
      grants = await api.list(id);
    } catch {
      onError?.(t("error_permissions", "Could not load permissions."));
    }
    if (resourceId !== id) return;
    initialById = new Map(grants.map((p: any) => [p.id, true]));
    staged = await Promise.all(grants.map(async (p: any) => ({
      id: p.id,
      targetType: p.target_type,
      targetCode: p.target_code,
      targetCodeLabel: await resolveTargetLabel(p.target_type, p.target_code, t("perm_public", "Public")),
      access: p.access_level,
    })));
  }

  /** Revoke removed grants, create new ones. Returns what each revoke answered. */
  export async function flush(id: number): Promise<any[]> {
    const revoked: any[] = [];
    const stagedIds = new Set(staged.filter((p) => p.id != null).map((p) => p.id));
    for (const [pid] of initialById) {
      if (!stagedIds.has(pid)) revoked.push(await api.revoke(pid));
    }
    for (const p of staged) {
      if (p.id != null) continue;
      const created = await api.create(id, {
        target_type: p.targetType,
        target_code: p.targetCode,
        access_level: p.access,
      });
      p.id = created.id;
    }
    staged = [...staged];
    initialById = new Map(staged.filter((p) => p.id != null).map((p) => [p.id as number, true]));
    return revoked;
  }

  export function reset(): void {
    resourceId = null;
    staged = [];
    initialById = new Map();
    permType = "";
    permCode = "";
    permCodeOptions = [];
    permCodeDisabled = false;
    permAccess = "";
    permError = "";
  }

  onMount(() => {
    void loadLists();
    const onLang = () => {
      langTick += 1;
    };
    window.addEventListener("languageChanged", onLang);
    document.addEventListener("synapxia:locale-changed", onLang);
    return () => {
      window.removeEventListener("languageChanged", onLang);
      document.removeEventListener("synapxia:locale-changed", onLang);
    };
  });

  const fieldClass =
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:border-gray-700 dark:bg-gray-800 dark:text-white";
  const labelClass = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1";
  const addBtnClass =
    "shrink-0 rounded-lg border border-indigo-600 px-4 py-2 text-sm font-semibold text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/30";
  const rowClass =
    "flex items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-white/[0.02] px-3 py-2";
  const emptyClass =
    "rounded-lg border border-dashed border-gray-300 dark:border-gray-700 p-6 text-center text-sm text-gray-500 dark:text-gray-400";
</script>

{#if !readonly}
  <section>
    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <div>
        <label for={`${idPrefix}-perm-target-type`} class={labelClass}>{t("perm_target_type", "Target type")}</label>
        <select id={`${idPrefix}-perm-target-type`} bind:value={permType} onchange={onPermTypeChange} class={fieldClass}>
          <option value="">{t("perm_choose_target_type", "— choose type —")}</option>
          {#each targetTypeOptions as o (o.value)}
            <option value={o.value}>{o.label}</option>
          {/each}
        </select>
      </div>
      <div>
        <label for={`${idPrefix}-perm-target-code`} class={labelClass}>{t("perm_target", "Target")}</label>
        <select id={`${idPrefix}-perm-target-code`} bind:value={permCode} disabled={permCodeDisabled} class={fieldClass}>
          <option value="">{t("perm_choose_target", "— choose target —")}</option>
          {#each permCodeOptions as o (o.value)}
            <option value={o.value}>{o.label}</option>
          {/each}
        </select>
      </div>
      <div>
        <label for={`${idPrefix}-perm-access`} class={labelClass}>{t("perm_access", "Access level")}</label>
        <select id={`${idPrefix}-perm-access`} bind:value={permAccess} class={fieldClass}>
          <option value="">{t("perm_choose_access", "— choose access —")}</option>
          {#each accessOptions as o (o.value)}
            <option value={o.value}>{o.label}</option>
          {/each}
        </select>
      </div>
      <div class="md:col-span-3 flex justify-end">
        <button type="button" class={addBtnClass} onclick={addPermission}>{t("perm_add", "Add permission")}</button>
      </div>
    </div>
    {#if permError}
      <p class="mt-2 text-xs text-red-600 dark:text-red-400">{permError}</p>
    {/if}
  </section>
{/if}
<section>
  {#if staged.length === 0}
    <div class={emptyClass}>{t("perm_empty", "No permissions yet.")}</div>
  {:else}
    <ul class="space-y-2">
      {#each staged as p, idx (p.id ?? `${p.targetType}:${p.targetCode}:${p.access}`)}
        <li
          class={p.id == null ? `${rowClass} ring-2 ring-amber-400` : rowClass}
          data-pending={p.id == null ? "1" : undefined}
        >
          <span class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-600 dark:bg-gray-700 dark:text-gray-300">{listText("TARGET_TYPE", p.targetType) || p.targetType}</span>
          <span class="min-w-0 flex-1 truncate text-sm font-semibold text-gray-800 dark:text-gray-200" title={p.targetCodeLabel}>{p.targetCode === PUBLIC_CODE && p.targetType === PUBLIC_TARGET ? t("perm_public", "Public") : p.targetCodeLabel}</span>
          <span class="shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">{listText("ACCESS_LEVEL", p.access) || p.access}</span>
          {#if !readonly}
            <button type="button" class="shrink-0 rounded-md p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/30" title={t("perm_remove", "Revoke")} aria-label={t("perm_remove", "Revoke")} onclick={() => removePermission(idx)}>
              <svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>
            </button>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</section>
