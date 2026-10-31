<script lang="ts">
  /**
   * PrivilegeMatrix — `/admin/privileges?profile=CODE`, the only screen that
   * defines a profile's privileges (without `?profile=` it opens the first one).
   *
   * Lists every active option of every active module as a checklist, the way
   * administration modules usually assign a profile's privileges: tick Access
   * to grant an option, tick Edit to also allow writes. A module's header
   * checkboxes act on its visible options at once. Nothing is written until
   * Save, which sends the whole set in one call (`PUT …/matrix`).
   *
   * Leaving with unsaved changes (profile switch or any in-app link) asks
   * through the same "Discard changes?" dialog the detail modals use. Closing
   * or reloading the tab can only use the browser's own prompt.
   */
  import { onMount } from "svelte";
  import { getPrivilegeMatrix, savePrivilegeMatrix } from "@/lib/privileges";
  import { getProfilesSelect } from "@/lib/profiles";
  import { apiErrorDetail } from "@/lib/api";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";
  import type { PrivilegeMatrixModule, PrivilegeMatrixEntry } from "@/types/api";

  let { profile }: { profile: string } = $props();

  type Access = { granted: boolean; edit: boolean };
  type View = "all" | "granted" | "missing";

  let langTick = $state(0);
  const t = (key: string, fallback: string): string => {
    void langTick;
    try {
      const v = translate(key);
      if (v && v !== key) return v;
    } catch {
      /* non-fatal */
    }
    return fallback;
  };
  const fmt = (s: string, vars: Record<string, string | number>) =>
    s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));

  let modules = $state<PrivilegeMatrixModule[]>([]);
  let profileName = $state("");
  let profiles = $state<{ value: string; label: string }[]>([]);
  let access = $state<Record<string, Access>>({});
  let initial = $state<Record<string, Access>>({});
  let collapsed = $state<Record<string, boolean>>({});
  let query = $state("");
  let view = $state<View>("all");
  let loading = $state(true);
  let loadError = $state(false);
  let saving = $state(false);

  let leaveDialog = $state<HTMLDialogElement | null>(null);
  let profileSelect = $state<HTMLSelectElement | null>(null);
  let pendingHref: string | null = null;

  const key = (module: string, option: string) => `${module}::${option}`;
  const moduleLabel = (m: PrivilegeMatrixModule) => t(`modules.${m.code}`, m.name);
  const optionLabel = (code: string, name: string) =>
    t(`menu_options.${code.toLowerCase()}`, name);

  function seed(data: { profile_name: string; modules: PrivilegeMatrixModule[] }) {
    profileName = data.profile_name;
    modules = data.modules;
    const next: Record<string, Access> = {};
    for (const m of data.modules)
      for (const o of m.options)
        next[key(m.code, o.code)] = { granted: o.granted, edit: o.granted && o.can_edit };
    access = next;
    initial = structuredClone(next);
  }

  async function load() {
    loading = true;
    loadError = false;
    try {
      seed(await getPrivilegeMatrix(profile));
    } catch (e) {
      loadError = true;
      showToast(apiErrorDetail(e, t("privilege_matrix.load_error", "Could not load the privileges")), "error");
    } finally {
      loading = false;
    }
  }

  // --- derived views ---------------------------------------------------------

  const changed = (k: string) =>
    access[k] && initial[k] &&
    (access[k].granted !== initial[k].granted || access[k].edit !== initial[k].edit);

  let changes = $derived(Object.keys(access).filter(changed).length);
  let totals = $derived.by(() => {
    const all = Object.values(access);
    return {
      options: all.length,
      granted: all.filter((a) => a.granted).length,
      edit: all.filter((a) => a.edit).length,
    };
  });

  let visible = $derived.by(() => {
    void langTick;
    const q = query.trim().toLowerCase();
    return modules
      .map((m) => {
        const moduleHit = q !== "" && (moduleLabel(m).toLowerCase().includes(q) || m.code.toLowerCase().includes(q));
        const options = m.options.filter((o) => {
          const a = access[key(m.code, o.code)];
          if (view === "granted" && !a?.granted) return false;
          if (view === "missing" && a?.granted) return false;
          if (!q || moduleHit) return true;
          return [optionLabel(o.code, o.name), o.name, o.code, o.path ?? ""]
            .some((s) => s.toLowerCase().includes(q));
        });
        return { module: m, options };
      })
      .filter((g) => g.options.length > 0);
  });

  /** "all" | "none" | "some" over the given options for one flag. */
  function groupState(module: string, codes: string[], flag: keyof Access) {
    const on = codes.filter((c) => access[key(module, c)]?.[flag]).length;
    return on === 0 ? "none" : on === codes.length ? "all" : "some";
  }

  // --- mutations -------------------------------------------------------------

  function setGranted(module: string, option: string, granted: boolean) {
    const a = access[key(module, option)];
    a.granted = granted;
    if (!granted) a.edit = false;
  }

  function setEdit(module: string, option: string, edit: boolean) {
    const a = access[key(module, option)];
    a.edit = edit;
    if (edit) a.granted = true;
  }

  function setGroup(module: string, codes: string[], flag: keyof Access, value: boolean) {
    for (const c of codes) (flag === "granted" ? setGranted : setEdit)(module, c, value);
  }

  // A search keeps every matching module open, so these act on the unfiltered list.
  let anyCollapsed = $derived(modules.some((m) => collapsed[m.code]));
  let allCollapsed = $derived(modules.length > 0 && modules.every((m) => collapsed[m.code]));

  function setAllCollapsed(value: boolean) {
    collapsed = Object.fromEntries(modules.map((m) => [m.code, value]));
  }

  function discard() {
    access = $state.snapshot(initial);
  }

  async function save() {
    if (saving || changes === 0) return;
    saving = true;
    const body: PrivilegeMatrixEntry[] = [];
    for (const [k, a] of Object.entries(access)) {
      if (!a.granted) continue;
      const [module, option] = k.split("::");
      body.push({ module, option, can_edit: a.edit });
    }
    try {
      seed(await savePrivilegeMatrix(profile, body));
      showToast(t("privilege_matrix.saved", "Privileges saved"), "success");
    } catch (e) {
      showToast(apiErrorDetail(e, t("privilege_matrix.save_error", "Could not save the privileges")), "error");
    } finally {
      saving = false;
    }
  }

  // --- leaving with unsaved changes -----------------------------------------

  function leave(href: string) {
    if (changes === 0) {
      window.location.href = href;
      return;
    }
    pendingHref = href;
    leaveDialog?.showModal();
  }

  function keepEditing() {
    pendingHref = null;
    if (profileSelect) profileSelect.value = profile;
    leaveDialog?.close();
  }

  function confirmLeave() {
    const href = pendingHref;
    leaveDialog?.close();
    if (!href) return;
    // Drop the dirty state so the beforeunload guard does not ask again.
    initial = $state.snapshot(access);
    window.location.href = href;
  }

  function switchProfile(code: string) {
    if (code !== profile) leave(`/admin/privileges?profile=${encodeURIComponent(code)}`);
  }

  /** Svelte action: drive a checkbox's indeterminate state. */
  function indeterminate(node: HTMLInputElement, value: boolean) {
    node.indeterminate = value;
    return { update: (v: boolean) => (node.indeterminate = v) };
  }

  onMount(() => {
    const onLang = () => (langTick += 1);
    const onUnload = (e: BeforeUnloadEvent) => {
      if (changes > 0) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    // In-app links (sidebar, breadcrumb, header) go through the dialog.
    const onLinkClick = (e: MouseEvent) => {
      if (changes === 0 || e.defaultPrevented || e.button !== 0) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!a || a.target === "_blank" || a.hasAttribute("download")) return;
      const url = new URL(a.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (url.pathname === window.location.pathname && url.search === window.location.search) return;
      e.preventDefault();
      leave(url.href);
    };
    window.addEventListener("languageChanged", onLang);
    window.addEventListener("beforeunload", onUnload);
    document.addEventListener("click", onLinkClick, true);
    if (profile) load();
    getProfilesSelect()
      .then((p) => {
        profiles = p || [];
        // Reached without `?profile=`: open the first profile.
        if (!profile) {
          const first = profiles[0]?.value;
          if (first) window.location.replace(`/admin/privileges?profile=${encodeURIComponent(first)}`);
          else (loading = false), (loadError = true);
        }
      })
      .catch(() => {
        if (!profile) (loading = false), (loadError = true);
      });
    return () => {
      window.removeEventListener("languageChanged", onLang);
      window.removeEventListener("beforeunload", onUnload);
      document.removeEventListener("click", onLinkClick, true);
    };
  });

  const box = "h-4 w-4 shrink-0 cursor-pointer rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-600 dark:bg-gray-800";
  const field = "rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100";
  // Access / Edit column cell: fixed width, divider on its left, full row height.
  const col = "flex w-20 shrink-0 items-center justify-center self-stretch border-l border-gray-200 sm:w-24 dark:border-gray-800";
  const ghost = "rounded-md p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-700 disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200";
  const chip = (on: boolean) =>
    `rounded-full px-3 py-1 text-xs font-medium transition ${on
      ? "bg-indigo-600 text-white"
      : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"}`;
</script>

<div class="space-y-4">
  <!-- Profile, summary and filters -->
  <div class="flex flex-col gap-4 rounded-xl border border-gray-200 bg-white p-4 lg:flex-row lg:items-center lg:justify-between dark:border-gray-800 dark:bg-white/[0.03]">
    <div class="min-w-0">
      <label for="pm-profile" class="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {t("privilege_matrix.profile", "Profile")}
      </label>
      {#if profiles.length}
        <select
          id="pm-profile"
          bind:this={profileSelect}
          class="{field} w-full min-w-[14rem] font-semibold sm:w-auto"
          value={profile}
          onchange={(e) => switchProfile((e.currentTarget as HTMLSelectElement).value)}
        >
          {#each profiles as p (p.value)}
            <option value={p.value}>{p.label}</option>
          {/each}
        </select>
      {:else}
        <p id="pm-profile" class="text-lg font-semibold text-gray-900 dark:text-white">{profileName || profile}</p>
      {/if}
      {#if !loading && !loadError}
        <p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
          <span class="font-semibold text-gray-900 dark:text-white">{totals.granted} / {totals.options}</span>
          {t("privilege_matrix.summary_access", "options with access")}
          <span class="mx-1.5 text-gray-300 dark:text-gray-600">·</span>
          <span class="font-semibold text-gray-900 dark:text-white">{totals.edit}</span>
          {t("privilege_matrix.summary_edit", "options that can be edited")}
        </p>
      {/if}
    </div>

    {#if !loading && !loadError}
      <div class="flex flex-col gap-2 lg:items-end">
        <input
          type="search"
          bind:value={query}
          placeholder={t("privilege_matrix.search", "Search options…")}
          aria-label={t("privilege_matrix.search", "Search options…")}
          class="{field} w-full lg:w-72"
        />
        <div class="flex flex-wrap items-center gap-2">
          <div class="flex flex-wrap gap-2" role="group" aria-label={t("privilege_matrix.show", "Show")}>
            <button type="button" class={chip(view === "all")} aria-pressed={view === "all"} onclick={() => (view = "all")}>
              {t("privilege_matrix.view_all", "All")}
            </button>
            <button type="button" class={chip(view === "granted")} aria-pressed={view === "granted"} onclick={() => (view = "granted")}>
              {t("privilege_matrix.view_granted", "With access")}
            </button>
            <button type="button" class={chip(view === "missing")} aria-pressed={view === "missing"} onclick={() => (view = "missing")}>
              {t("privilege_matrix.view_missing", "Without access")}
            </button>
          </div>
          <!-- Expand / collapse every module: icon-only, name on hover. -->
          <span class="h-5 w-px bg-gray-200 dark:bg-gray-700" aria-hidden="true"></span>
          <div class="flex gap-0.5">
            <button
              type="button"
              class={ghost}
              onclick={() => setAllCollapsed(false)}
              disabled={query.trim() !== "" || !anyCollapsed}
              title={t("privilege_matrix.expand_all", "Expand all")}
              aria-label={t("privilege_matrix.expand_all", "Expand all")}
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M10 3a.75.75 0 01.55.24l3.25 3.5a.75.75 0 11-1.1 1.02L10 4.85 7.3 7.76a.75.75 0 01-1.1-1.02l3.25-3.5A.75.75 0 0110 3zm-3.76 9.2a.75.75 0 011.06.04l2.7 2.91 2.7-2.91a.75.75 0 111.1 1.02l-3.25 3.5a.75.75 0 01-1.1 0l-3.25-3.5a.75.75 0 01.04-1.06z" clip-rule="evenodd" />
              </svg>
            </button>
            <button
              type="button"
              class={ghost}
              onclick={() => setAllCollapsed(true)}
              disabled={query.trim() !== "" || allCollapsed}
              title={t("privilege_matrix.collapse_all", "Collapse all")}
              aria-label={t("privilege_matrix.collapse_all", "Collapse all")}
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M6.24 3.2a.75.75 0 011.06.04L10 6.15l2.7-2.91a.75.75 0 111.1 1.02l-3.25 3.5a.75.75 0 01-1.1 0L6.2 4.26a.75.75 0 01.04-1.06zm3.21 9.04a.75.75 0 011.1 0l3.25 3.5a.75.75 0 11-1.1 1.02L10 13.85l-2.7 2.91a.75.75 0 11-1.1-1.02l3.25-3.5z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    {/if}
  </div>

  {#if loading}
    <p class="py-10 text-center text-sm text-gray-500 dark:text-gray-400">{t("privilege_matrix.loading", "Loading…")}</p>
  {:else if loadError}
    <div class="py-10 text-center">
      <button type="button" class="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400" onclick={() => (profile ? load() : window.location.reload())}>
        {t("privilege_matrix.retry", "Try again")}
      </button>
    </div>
  {:else}
    {#if visible.length === 0}
      <p class="rounded-xl border border-dashed border-gray-300 py-10 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
        {t("privilege_matrix.empty", "No options match")}
      </p>
    {/if}

    {#each visible as g (g.module.code)}
      {@const codes = g.options.map((o) => o.code)}
      {@const all = g.module.options.map((o) => o.code)}
      {@const accessState = groupState(g.module.code, codes, "granted")}
      {@const editState = groupState(g.module.code, codes, "edit")}
      {@const open = !collapsed[g.module.code] || query.trim() !== ""}
      <section class="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.03]">
        <header class="flex items-stretch border-b border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-white/[0.02]">
          <button
            type="button"
            class="flex min-w-0 flex-1 items-center gap-2 px-4 py-2.5 text-left"
            aria-expanded={open}
            onclick={() => (collapsed[g.module.code] = !collapsed[g.module.code])}
          >
            <svg class="h-4 w-4 shrink-0 text-gray-400 transition {open ? 'rotate-90' : ''}" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.17 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
            </svg>
            <span class="truncate text-sm font-semibold text-gray-900 dark:text-white">{moduleLabel(g.module)}</span>
            <span class="shrink-0 rounded-full bg-gray-200 px-2 py-0.5 text-[11px] font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">
              {all.filter((c) => access[key(g.module.code, c)]?.granted).length}/{all.length}
            </span>
          </button>
          <label class="{col} cursor-pointer flex-col gap-1 py-1.5">
            <span class="text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{t("privilege_matrix.access", "Access")}</span>
            <input
              type="checkbox"
              class={box}
              checked={accessState === "all"}
              use:indeterminate={accessState === "some"}
              onchange={(e) => setGroup(g.module.code, codes, "granted", (e.currentTarget as HTMLInputElement).checked)}
              aria-label={fmt(t("privilege_matrix.access_all", "Access to every option in {module}"), { module: moduleLabel(g.module) })}
            />
          </label>
          <label class="{col} cursor-pointer flex-col gap-1 py-1.5">
            <span class="text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{t("privilege_matrix.edit", "Edit")}</span>
            <input
              type="checkbox"
              class={box}
              checked={editState === "all"}
              use:indeterminate={editState === "some"}
              onchange={(e) => setGroup(g.module.code, codes, "edit", (e.currentTarget as HTMLInputElement).checked)}
              aria-label={fmt(t("privilege_matrix.edit_all", "Edit on every option in {module}"), { module: moduleLabel(g.module) })}
            />
          </label>
        </header>

        {#if open}
          <ul class="divide-y divide-gray-100 dark:divide-gray-800">
            {#each g.options as o (o.code)}
              {@const k = key(g.module.code, o.code)}
              {@const a = access[k]}
              <li class="flex items-stretch {changed(k) ? 'bg-amber-50 dark:bg-amber-500/10' : ''}">
                <div class="flex min-w-0 flex-1 items-center gap-2 py-2 pl-10 pr-4">
                  {#if changed(k)}
                    <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" title={t("privilege_matrix.unsaved", "Unsaved change")}></span>
                  {/if}
                  <div class="min-w-0">
                    <p class="truncate text-sm text-gray-900 dark:text-gray-100">{optionLabel(o.code, o.name)}</p>
                    <p class="truncate font-mono text-[11px] text-gray-400 dark:text-gray-500">
                      {o.code}{#if o.path}<span class="ml-2">{o.path}</span>{/if}
                    </p>
                  </div>
                </div>
                <div class={col}>
                  <input
                    type="checkbox"
                    class={box}
                    checked={a.granted}
                    onchange={(e) => setGranted(g.module.code, o.code, (e.currentTarget as HTMLInputElement).checked)}
                    aria-label={fmt(t("privilege_matrix.access_one", "Access to {option}"), { option: optionLabel(o.code, o.name) })}
                  />
                </div>
                <div class={col}>
                  <input
                    type="checkbox"
                    class={box}
                    checked={a.edit}
                    onchange={(e) => setEdit(g.module.code, o.code, (e.currentTarget as HTMLInputElement).checked)}
                    aria-label={fmt(t("privilege_matrix.edit_one", "Edit on {option}"), { option: optionLabel(o.code, o.name) })}
                  />
                </div>
              </li>
            {/each}
          </ul>
        {/if}
      </section>
    {/each}
  {/if}

  <!-- Save bar: sticks to the bottom of the content column while there are changes. -->
  {#if changes > 0}
    <div class="sticky bottom-4 z-30 flex flex-col gap-3 rounded-xl border border-gray-200 bg-white/95 px-4 py-3 shadow-lg backdrop-blur sm:flex-row sm:items-center sm:justify-between dark:border-gray-800 dark:bg-gray-900/95">
      <p class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
        <span class="h-2 w-2 shrink-0 rounded-full bg-amber-500" aria-hidden="true"></span>
        {fmt(t("privilege_matrix.pending", "{count} unsaved change(s)"), { count: changes })}
      </p>
      <div class="flex justify-end gap-3">
        <button type="button" class="rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-50 dark:text-gray-200 dark:hover:bg-gray-800" onclick={discard} disabled={saving}>
          {t("privilege_matrix.discard", "Discard")}
        </button>
        <button type="button" class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50" onclick={save} disabled={saving}>
          {saving ? t("privilege_matrix.saving", "Saving…") : t("privilege_matrix.save", "Save privileges")}
        </button>
      </div>
    </div>
  {/if}
</div>

<!-- Same "Discard changes?" dialog as AssetDetailModal / ProcessDetailModal. -->
<dialog
  bind:this={leaveDialog}
  oncancel={(e) => { e.preventDefault(); keepEditing(); }}
  class="rounded-2xl p-6 w-[420px] max-w-full bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100 backdrop:bg-black/60 backdrop:backdrop-blur-sm"
>
  <h3 class="text-base font-bold text-gray-900 dark:text-white">
    {t("privilege_matrix.discard_title", "Discard changes?")}
  </h3>
  <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
    {t("privilege_matrix.discard_message", "You have unsaved changes. If you leave now, they will be lost.")}
  </p>
  <div class="mt-5 flex justify-end gap-3">
    <button
      type="button"
      class="rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
      onclick={keepEditing}
    >
      {t("privilege_matrix.discard_keep_editing", "Keep editing")}
    </button>
    <button
      type="button"
      class="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
      onclick={confirmLeave}
    >
      {t("privilege_matrix.discard_confirm", "Discard changes")}
    </button>
  </div>
</dialog>
