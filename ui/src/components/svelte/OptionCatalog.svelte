<script lang="ts">
  /**
   * OptionCatalog — `/admin/options`, laid out like the privilege checklist
   * (PrivilegeMatrix.svelte): one section per active module, its header
   * carrying the module (icon, name, code), its rows the module's options
   * (icon, name, code, path, type, order).
   *
   * Reads `GET /api/options/catalog` (not scoped to the caller's privileges).
   * Create, edit and remove go through the single-row option routes, one
   * option at a time, from a dialog; the catalog is reloaded after each.
   */
  import { onMount } from "svelte";
  import { getOptionCatalog, createOption, updateOption, deleteOption } from "@/lib/options";
  import { getListItemsbyList } from "@/lib/list_items";
  import { labelsByValue, listLabel, toListOptions, type ListItemLike } from "@/lib/listLang";
  import { iconSvg, ALL_ICON_SLUGS } from "@/lib/profileIcons";
  import { apiErrorDetail } from "@/lib/api";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";
  import type { OptionCatalogModule, OptionCatalogOption } from "@/types/api";

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

  let modules = $state<OptionCatalogModule[]>([]);
  let typeItems = $state<ListItemLike[]>([]);
  let collapsed = $state<Record<string, boolean>>({});
  let query = $state("");
  let moduleFilter = $state("");
  let loading = $state(true);
  let loadError = $state(false);

  const moduleLabel = (m: { code: string; name: string }) => t(`modules.${m.code}`, m.name);
  const optionLabel = (o: { code: string; name: string }) =>
    t(`menu_options.${o.code.toLowerCase()}`, o.name);
  let typeLabels = $derived(labelsByValue(typeItems));
  const typeLabel = (v: string) => (void langTick, listLabel(typeLabels, v));
  let typeOptions = $derived((void langTick, toListOptions(typeItems)));

  async function load() {
    loading = true;
    loadError = false;
    try {
      modules = await getOptionCatalog();
    } catch (e) {
      loadError = true;
      showToast(apiErrorDetail(e, t("option_catalog.load_error", "Could not load the options")), "error");
    } finally {
      loading = false;
    }
  }

  // --- derived views ---------------------------------------------------------

  let totalOptions = $derived(modules.reduce((n, m) => n + m.options.length, 0));

  let visible = $derived.by(() => {
    void langTick;
    const q = query.trim().toLowerCase();
    return modules
      .filter((m) => !moduleFilter || m.code === moduleFilter)
      .map((m) => {
        const moduleHit = q !== "" && (moduleLabel(m).toLowerCase().includes(q) || m.code.toLowerCase().includes(q));
        const options = m.options.filter((o) =>
          !q || moduleHit ||
          [optionLabel(o), o.name, o.code, o.path ?? "", typeLabel(o.type)].some((s) => s.toLowerCase().includes(q)));
        return { module: m, options, moduleHit };
      })
      // An empty module stays listed when nothing is searched, so it can get options.
      .filter((g) => g.options.length > 0 || (!q && g.module.options.length === 0) || g.moduleHit);
  });

  let anyCollapsed = $derived(modules.some((m) => collapsed[m.code]));
  let allCollapsed = $derived(modules.length > 0 && modules.every((m) => collapsed[m.code]));

  function setAllCollapsed(value: boolean) {
    collapsed = Object.fromEntries(modules.map((m) => [m.code, value]));
  }

  // --- create / edit dialog --------------------------------------------------

  type Form = {
    module: string; code: string; name: string; path: string; type: string;
    sort_order: string; icon: string; description: string;
  };
  let formDialog = $state<HTMLDialogElement | null>(null);
  let deleteDialog = $state<HTMLDialogElement | null>(null);
  let editing = $state<{ module: string; code: string } | null>(null);
  let form = $state<Form>(blank(""));
  let iconQuery = $state("");
  let saving = $state(false);
  let removing = $state<{ module: OptionCatalogModule; option: OptionCatalogOption } | null>(null);

  function blank(module: string): Form {
    const m = modules.find((x) => x.code === module);
    const next = m && m.options.length ? Math.max(...m.options.map((o) => o.sort_order)) + 10 : 10;
    return {
      module, code: "", name: "", path: "", type: typeOptions[0]?.value ?? "FORM",
      sort_order: String(next), icon: "", description: "",
    };
  }

  function openCreate(module = moduleFilter || modules[0]?.code || "") {
    editing = null;
    form = blank(module);
    iconQuery = "";
    formDialog?.showModal();
  }

  function openEdit(m: OptionCatalogModule, o: OptionCatalogOption) {
    editing = { module: m.code, code: o.code };
    form = {
      module: m.code, code: o.code, name: o.name, path: o.path ?? "", type: o.type,
      sort_order: String(o.sort_order), icon: o.icon ?? "", description: o.description ?? "",
    };
    iconQuery = "";
    formDialog?.showModal();
  }

  let iconChoices = $derived.by(() => {
    const q = iconQuery.trim().toLowerCase();
    return q ? ALL_ICON_SLUGS.filter((s) => s.includes(q)) : ALL_ICON_SLUGS;
  });

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    if (saving) return;
    saving = true;
    const fields = {
      name: form.name.trim(),
      path: form.path.trim() || undefined,
      type: form.type,
      sort_order: Number(form.sort_order) || 0,
      icon: form.icon || undefined,
      description: form.description.trim() || undefined,
    };
    try {
      if (editing) {
        // Send blanks as null so a cleared icon/path/description is cleared.
        await updateOption(editing.module, editing.code, {
          ...fields,
          path: fields.path ?? (null as unknown as string),
          icon: fields.icon ?? (null as unknown as string),
          description: fields.description ?? (null as unknown as string),
        });
        showToast(t("option_catalog.updated", "Option updated"), "success");
      } else {
        await createOption({ module: form.module, code: form.code.trim(), ...fields });
        showToast(t("option_catalog.created", "Option created"), "success");
      }
      formDialog?.close();
      await load();
    } catch (err) {
      showToast(apiErrorDetail(err, t("option_catalog.save_error", "Could not save the option")), "error");
    } finally {
      saving = false;
    }
  }

  function askDelete(m: OptionCatalogModule, o: OptionCatalogOption) {
    removing = { module: m, option: o };
    deleteDialog?.showModal();
  }

  async function confirmDelete() {
    if (!removing || saving) return;
    saving = true;
    try {
      await deleteOption(removing.module.code, removing.option.code);
      showToast(t("option_catalog.deleted", "Option removed"), "success");
      deleteDialog?.close();
      await load();
    } catch (err) {
      showToast(apiErrorDetail(err, t("option_catalog.delete_error", "Could not remove the option")), "error");
    } finally {
      saving = false;
    }
  }

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);
    load();
    getListItemsbyList("OPTION_TYPE")
      .then((items) => (typeItems = items || []))
      .catch(() => {});
    return () => window.removeEventListener("languageChanged", onLang);
  });

  const field = "rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none disabled:bg-gray-100 disabled:text-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:disabled:bg-gray-800";
  const label = "mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400";
  const ghost = "rounded-md p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-700 disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200";
  // Order column cell: fixed width, divider on its left, full row height (as in the checklist).
  const col = "flex w-16 shrink-0 items-center justify-center self-stretch border-l border-gray-200 sm:w-20 dark:border-gray-800";
</script>

<div class="space-y-4">
  <!-- Summary, search and filters, as the checklist's top card. -->
  <div class="grid gap-x-6 gap-y-3 rounded-xl border border-gray-200 bg-white p-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center dark:border-gray-800 dark:bg-white/[0.03]">
    <div class="flex min-w-0 items-center gap-3 lg:col-start-1 lg:row-start-1">
      <label for="oc-module" class="shrink-0 text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {t("option_modal.module", "Module")}
      </label>
      <select id="oc-module" bind:value={moduleFilter} class="{field} min-w-0 flex-1 font-semibold sm:min-w-[14rem] sm:flex-none">
        <option value="">{t("option_catalog.all_modules", "All modules")}</option>
        {#each modules as m (m.code)}
          <option value={m.code}>{moduleLabel(m)}</option>
        {/each}
      </select>
    </div>
    {#if !loading && !loadError}
      <p class="text-xs text-gray-500 lg:col-start-1 lg:row-start-2 dark:text-gray-400">
        <span class="font-semibold text-gray-900 dark:text-white">{modules.length}</span>
        {t("option_catalog.summary_modules", "modules")}
        <span class="mx-1.5 text-gray-300 dark:text-gray-600">·</span>
        <span class="font-semibold text-gray-900 dark:text-white">{totalOptions}</span>
        {t("option_catalog.summary_options", "options")}
      </p>
    {/if}
    <input
      type="search"
      bind:value={query}
      placeholder={t("option_catalog.search", "Search options…")}
      aria-label={t("option_catalog.search", "Search options…")}
      class="{field} w-full lg:col-start-2 lg:row-start-1 lg:w-72"
    />
    <div class="flex flex-wrap items-center gap-2 lg:col-start-2 lg:row-start-2 lg:justify-end">
      <button
        type="button"
        class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
        onclick={() => openCreate()}
        disabled={loading || loadError || modules.length === 0}
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
        </svg>
        {t("option_modal.add_new", "New Option")}
      </button>
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

  {#if loading}
    <p class="py-10 text-center text-sm text-gray-500 dark:text-gray-400">{t("privilege_matrix.loading", "Loading…")}</p>
  {:else if loadError}
    <div class="py-10 text-center">
      <button type="button" class="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400" onclick={load}>
        {t("privilege_matrix.retry", "Try again")}
      </button>
    </div>
  {:else}
    {#if visible.length === 0}
      <p class="rounded-xl border border-dashed border-gray-300 py-10 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
        {t("option_modal.empty_message", "No Options found")}
      </p>
    {/if}

    {#each visible as g (g.module.code)}
      {@const open = !collapsed[g.module.code] || query.trim() !== ""}
      {@const mIcon = iconSvg(g.module.icon)}
      <section class="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.03]">
        <header class="flex items-stretch border-b border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-white/[0.02]">
          <button
            type="button"
            class="flex min-w-0 flex-1 items-center gap-3 px-4 py-2.5 text-left"
            aria-expanded={open}
            onclick={() => (collapsed[g.module.code] = !collapsed[g.module.code])}
          >
            <svg class="h-4 w-4 shrink-0 text-gray-400 transition {open ? 'rotate-90' : ''}" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.17 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
            </svg>
            <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300 [&>svg]:h-5 [&>svg]:w-5" aria-hidden="true">
              {#if mIcon}{@html mIcon}{/if}
            </span>
            <span class="min-w-0">
              <span class="block truncate text-sm font-semibold text-gray-900 dark:text-white">{moduleLabel(g.module)}</span>
              <span class="block truncate font-mono text-[11px] text-gray-400 dark:text-gray-500">{g.module.code}</span>
            </span>
            <span class="shrink-0 rounded-full bg-gray-200 px-2 py-0.5 text-[11px] font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">
              {g.module.options.length}
            </span>
          </button>
          <div class="{col} flex-col gap-1 py-1.5">
            <span class="text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{t("option_catalog.order", "Order")}</span>
          </div>
          <div class="flex w-20 shrink-0 items-center justify-center self-stretch border-l border-gray-200 dark:border-gray-800">
            <button
              type="button"
              class={ghost}
              onclick={() => openCreate(g.module.code)}
              title={fmt(t("option_catalog.add_to", "New option in {module}"), { module: moduleLabel(g.module) })}
              aria-label={fmt(t("option_catalog.add_to", "New option in {module}"), { module: moduleLabel(g.module) })}
            >
              <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
              </svg>
            </button>
          </div>
        </header>

        {#if open}
          {#if g.options.length === 0}
            <p class="py-4 pl-[4.25rem] pr-4 text-sm text-gray-400 dark:text-gray-500">{t("option_catalog.module_empty", "This module has no options yet")}</p>
          {:else}
            <ul class="divide-y divide-gray-100 dark:divide-gray-800">
              {#each g.options as o (o.code)}
                {@const oIcon = iconSvg(o.icon)}
                <li class="flex items-stretch">
                  <div class="flex min-w-0 flex-1 items-center gap-3 py-2 pl-[4.25rem] pr-4">
                    <span class="flex h-5 w-5 shrink-0 items-center justify-center text-gray-500 dark:text-gray-400 [&>svg]:h-5 [&>svg]:w-5" aria-hidden="true">
                      {#if oIcon}{@html oIcon}{/if}
                    </span>
                    <div class="min-w-0 flex-1">
                      <p class="truncate text-sm text-gray-900 dark:text-gray-100">{optionLabel(o)}</p>
                      <p class="truncate font-mono text-[11px] text-gray-400 dark:text-gray-500">
                        {o.code}{#if o.path}<span class="ml-2">{o.path}</span>{/if}
                      </p>
                    </div>
                    <span class="hidden shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-600 sm:inline dark:bg-gray-800 dark:text-gray-300">
                      {typeLabel(o.type)}
                    </span>
                  </div>
                  <div class="{col} text-sm tabular-nums text-gray-600 dark:text-gray-300">{o.sort_order}</div>
                  <div class="flex w-20 shrink-0 items-center justify-center gap-0.5 self-stretch border-l border-gray-200 dark:border-gray-800">
                    <button
                      type="button"
                      class={ghost}
                      onclick={() => openEdit(g.module, o)}
                      title={t("option_modal.edit", "Edit Option")}
                      aria-label={`${t("option_modal.edit", "Edit Option")}: ${optionLabel(o)}`}
                    >
                      <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path d="M5.433 13.917l1.262-3.155A4 4 0 017.58 9.42l6.92-6.918a2.121 2.121 0 013 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 01-.65-.65z" />
                        <path d="M3.5 5.75c0-.69.56-1.25 1.25-1.25H10A.75.75 0 0010 3H4.75A2.75 2.75 0 002 5.75v9.5A2.75 2.75 0 004.75 18h9.5A2.75 2.75 0 0017 15.25V10a.75.75 0 00-1.5 0v5.25c0 .69-.56 1.25-1.25 1.25h-9.5c-.69 0-1.25-.56-1.25-1.25v-9.5z" />
                      </svg>
                    </button>
                    <button
                      type="button"
                      class="{ghost} hover:!text-red-600 dark:hover:!text-red-400"
                      onclick={() => askDelete(g.module, o)}
                      title={t("option_modal.delete", "Delete Option")}
                      aria-label={`${t("option_modal.delete", "Delete Option")}: ${optionLabel(o)}`}
                    >
                      <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fill-rule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clip-rule="evenodd" />
                      </svg>
                    </button>
                  </div>
                </li>
              {/each}
            </ul>
          {/if}
        {/if}
      </section>
    {/each}
  {/if}
</div>

<!-- Create / edit one option. -->
<dialog
  bind:this={formDialog}
  class="w-[640px] max-w-[calc(100%-2rem)] rounded-2xl bg-white p-0 text-gray-900 backdrop:bg-black/60 backdrop:backdrop-blur-sm dark:bg-gray-900 dark:text-gray-100"
>
  <form onsubmit={submit} class="flex max-h-[85vh] flex-col">
    <div class="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-gray-800">
      <h3 class="text-base font-bold text-gray-900 dark:text-white">
        {editing ? t("option_modal.edit", "Edit Option") : t("option_modal.add_new", "New Option")}
      </h3>
      <button type="button" class={ghost} onclick={() => formDialog?.close()} aria-label={t("option_catalog.close", "Close")}>
        <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
        </svg>
      </button>
    </div>

    <div class="grid gap-4 overflow-y-auto px-6 py-5 sm:grid-cols-2">
      <div>
        <label for="oc-f-module" class={label}><span class="text-red-500">*</span> {t("option_modal.module", "Module")}</label>
        <select id="oc-f-module" class="{field} w-full" bind:value={form.module} disabled={!!editing} required>
          {#each modules as m (m.code)}
            <option value={m.code}>{moduleLabel(m)}</option>
          {/each}
        </select>
      </div>
      <div>
        <label for="oc-f-code" class={label}><span class="text-red-500">*</span> {t("option_modal.code", "Code")}</label>
        <input id="oc-f-code" class="{field} w-full font-mono" bind:value={form.code} disabled={!!editing} required maxlength="50" />
      </div>
      <div>
        <label for="oc-f-name" class={label}><span class="text-red-500">*</span> {t("option_modal.name", "Name")}</label>
        <input id="oc-f-name" class="{field} w-full" bind:value={form.name} required maxlength="100" />
      </div>
      <div>
        <label for="oc-f-path" class={label}>{t("option_modal.path", "Path")}</label>
        <input id="oc-f-path" class="{field} w-full font-mono" bind:value={form.path} />
      </div>
      <div>
        <label for="oc-f-type" class={label}><span class="text-red-500">*</span> {t("option_modal.type", "Type")}</label>
        <select id="oc-f-type" class="{field} w-full" bind:value={form.type} required>
          {#each typeOptions as opt (opt.value)}
            <option value={opt.value}>{opt.label}</option>
          {/each}
          {#if form.type && !typeOptions.some((o) => o.value === form.type)}
            <option value={form.type}>{form.type}</option>
          {/if}
        </select>
      </div>
      <div>
        <label for="oc-f-order" class={label}><span class="text-red-500">*</span> {t("option_modal.sort_order", "Sort Order")}</label>
        <input id="oc-f-order" type="number" class="{field} w-full" bind:value={form.sort_order} required />
      </div>
      <div class="sm:col-span-2">
        <label for="oc-f-description" class={label}>{t("option_catalog.description", "Description")}</label>
        <textarea id="oc-f-description" rows="2" class="{field} w-full" bind:value={form.description} maxlength="500"></textarea>
      </div>
      <div class="sm:col-span-2">
        <div class="mb-1 flex items-center justify-between gap-3">
          <span class={label}>{t("option_modal.icon", "Icon")}</span>
          <input
            type="search"
            bind:value={iconQuery}
            placeholder={t("option_catalog.icon_search", "Search icons…")}
            aria-label={t("option_catalog.icon_search", "Search icons…")}
            class="{field} w-44 py-1 text-xs"
          />
        </div>
        <div class="grid max-h-48 grid-cols-6 gap-1.5 overflow-y-auto rounded-lg border border-gray-200 p-2 sm:grid-cols-10 dark:border-gray-800" role="radiogroup" aria-label={t("option_modal.icon", "Icon")}>
          <button
            type="button"
            role="radio"
            aria-checked={form.icon === ""}
            class="flex h-9 items-center justify-center rounded-md border text-[10px] {form.icon === '' ? 'border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300' : 'border-transparent text-gray-400 hover:border-gray-300 dark:hover:border-gray-700'}"
            onclick={() => (form.icon = "")}
            title={t("option_catalog.no_icon", "No icon")}
          >
            {t("option_catalog.no_icon", "No icon")}
          </button>
          {#each iconChoices as slug (slug)}
            <button
              type="button"
              role="radio"
              aria-checked={form.icon === slug}
              class="flex h-9 items-center justify-center rounded-md border [&>svg]:h-5 [&>svg]:w-5 {form.icon === slug ? 'border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300' : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-indigo-600 dark:text-gray-400 dark:hover:border-gray-700'}"
              onclick={() => (form.icon = slug)}
              title={slug}
              aria-label={slug}
            >
              {@html iconSvg(slug)}
            </button>
          {/each}
        </div>
        {#if form.icon}
          <p class="mt-1 font-mono text-[11px] text-gray-400 dark:text-gray-500">{form.icon}</p>
        {/if}
      </div>
    </div>

    <div class="flex justify-end gap-3 border-t border-gray-200 px-6 py-4 dark:border-gray-800">
      <button type="button" class="rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800" onclick={() => formDialog?.close()}>
        {t("option_catalog.cancel", "Cancel")}
      </button>
      <button type="submit" class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50" disabled={saving}>
        {saving ? t("privilege_matrix.saving", "Saving…") : t("option_catalog.save", "Save")}
      </button>
    </div>
  </form>
</dialog>

<!-- Remove one option (logical delete). -->
<dialog
  bind:this={deleteDialog}
  class="rounded-2xl p-6 w-[420px] max-w-full bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100 backdrop:bg-black/60 backdrop:backdrop-blur-sm"
>
  <h3 class="text-base font-bold text-gray-900 dark:text-white">{t("option_modal.delete", "Delete Option")}</h3>
  <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
    {t("option_modal.delete_confirmation", "Are you sure you want to delete this Option")}
    {#if removing}<span class="font-semibold text-gray-900 dark:text-white">{optionLabel(removing.option)}</span>
      <span class="font-mono text-xs text-gray-400">({removing.module.code}/{removing.option.code})</span>{/if}
  </p>
  <div class="mt-5 flex justify-end gap-3">
    <button type="button" class="rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800" onclick={() => deleteDialog?.close()}>
      {t("option_catalog.cancel", "Cancel")}
    </button>
    <button type="button" class="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50" onclick={confirmDelete} disabled={saving}>
      {t("option_catalog.delete_confirm", "Delete")}
    </button>
  </div>
</dialog>
