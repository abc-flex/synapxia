<script lang="ts">
  /**
   * SpecificationMatrix — `/taxo/specifications?category=CODE` (without
   * `?category=` it opens the first category). Same layout as PrivilegeMatrix:
   * a selector card on top, one collapsible section per feature type, a sticky
   * save bar.
   *
   * Lists every active feature as a checklist: tick Included to specify the
   * feature for the category, then set its order and default value and tick
   * Required / Copyable (either one also ticks Included). A section's header
   * checkboxes act on its visible features at once. Nothing is written until
   * Save, which sends the whole set in one call
   * (`PUT /api/specifications/category/{code}/matrix`).
   *
   * Leaving with unsaved changes (category switch or any in-app link) asks
   * through the same "Discard changes?" dialog the detail modals use.
   */
  import { onMount } from "svelte";
  import { getSpecificationMatrix, saveSpecificationMatrix } from "@/lib/specifications";
  import { getCategories } from "@/lib/categories";
  import { getListItemsbyList } from "@/lib/list_items";
  import { labelsByValue, listLabel, toListOptions } from "@/lib/listLang";
  import { apiErrorDetail } from "@/lib/api";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";
  import type {
    Category, ListItem, SpecificationMatrix, SpecificationMatrixEntry, SpecificationMatrixFeature,
  } from "@/types/api";

  let { category }: { category: string } = $props();

  type Spec = { specified: boolean; required: boolean; copyable: boolean; sort_order: number; default_value: string };
  type Flag = "specified" | "required" | "copyable";
  type View = "all" | "specified" | "missing";

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

  let features = $state<SpecificationMatrixFeature[]>([]);
  let categoryName = $state("");
  let categories = $state<{ value: string; label: string }[]>([]);
  let featureTypes = $state<ListItem[]>([]);
  // list code → its items (every language), for list-backed default values.
  let listItems = $state<Record<string, ListItem[]>>({});
  let specs = $state<Record<string, Spec>>({});
  let initial = $state<Record<string, Spec>>({});
  let collapsed = $state<Record<string, boolean>>({});
  let query = $state("");
  let view = $state<View>("all");
  let loading = $state(true);
  let loadError = $state(false);
  let saving = $state(false);

  let leaveDialog = $state<HTMLDialogElement | null>(null);
  let categorySelect = $state<HTMLSelectElement | null>(null);
  let pendingHref: string | null = null;

  function seed(data: SpecificationMatrix) {
    categoryName = data.category_name;
    const next: Record<string, Spec> = {};
    for (const f of data.features)
      next[f.code] = {
        specified: f.specified,
        required: f.specified && f.required,
        copyable: f.specified && f.copyable,
        sort_order: f.sort_order,
        default_value: f.default_value ?? "",
      };
    // Specified features first in their configured order, the rest by name.
    // Sorted once here, so a row never jumps while its order is being typed.
    features = [...data.features].sort((a, b) =>
      Number(b.specified) - Number(a.specified) ||
      (a.specified ? a.sort_order - b.sort_order : 0) ||
      a.name.localeCompare(b.name));
    specs = next;
    initial = structuredClone(next);
    loadLists(data.features);
  }

  function loadLists(all: SpecificationMatrixFeature[]) {
    const codes = [...new Set(all.map((f) => f.list).filter((l): l is string => !!l))];
    for (const code of codes) {
      if (listItems[code]) continue;
      // Options are a convenience: a failed list keeps the plain text input.
      getListItemsbyList(code, 0, 500).then((items) => (listItems[code] = items || [])).catch(() => {});
    }
  }

  async function load() {
    loading = true;
    loadError = false;
    try {
      seed(await getSpecificationMatrix(category));
    } catch (e) {
      loadError = true;
      showToast(apiErrorDetail(e, t("specification_matrix.load_error", "Could not load the specifications")), "error");
    } finally {
      loading = false;
    }
  }

  /** Categories as a tree: parents first, children indented under them. */
  function categoryTree(rows: Category[]) {
    const active = rows.filter((c) => c.is_active !== false);
    const codes = new Set(active.map((c) => c.code));
    const children = new Map<string, Category[]>();
    for (const c of active) {
      const parent = c.parent && codes.has(c.parent) ? c.parent : "";
      children.set(parent, [...(children.get(parent) ?? []), c]);
    }
    const out: { value: string; label: string }[] = [];
    const walk = (parent: string, depth: number, seen: Set<string>) => {
      for (const c of (children.get(parent) ?? []).sort((a, b) => a.name.localeCompare(b.name))) {
        if (seen.has(c.code)) continue;
        seen.add(c.code);
        out.push({ value: c.code, label: `${"   ".repeat(depth)}${c.name}` });
        walk(c.code, depth + 1, seen);
      }
    };
    walk("", 0, new Set());
    return out;
  }

  // --- derived views ---------------------------------------------------------

  const typeLabel = (type: string) => {
    void langTick;
    return type ? listLabel(labelsByValue(featureTypes), type) || type : t("specification_matrix.no_type", "No type");
  };

  /** One feature's options when it is list-backed (keeping an unknown saved value). */
  function valueOptions(f: SpecificationMatrixFeature, current: string) {
    void langTick;
    const items = f.list ? listItems[f.list] : undefined;
    if (!items) return null;
    const options = toListOptions(items);
    if (current && !options.some((o) => o.value === current))
      options.unshift({ value: current, label: current, labels: { en: current } });
    return options;
  }

  const same = (a: Spec, b: Spec) =>
    a.specified === b.specified &&
    (!a.specified ||
      (a.required === b.required && a.copyable === b.copyable &&
        Number(a.sort_order) === Number(b.sort_order) &&
        a.default_value.trim() === b.default_value.trim()));

  const changed = (code: string) => specs[code] && initial[code] && !same(specs[code], initial[code]);
  const badOrder = (code: string) => specs[code]?.specified && !Number.isInteger(Number(specs[code].sort_order));

  let changes = $derived(Object.keys(specs).filter(changed).length);
  let invalid = $derived(Object.keys(specs).some(badOrder));
  let totals = $derived.by(() => {
    const all = Object.values(specs);
    return {
      features: all.length,
      specified: all.filter((s) => s.specified).length,
      required: all.filter((s) => s.required).length,
      copyable: all.filter((s) => s.copyable).length,
    };
  });

  /** Feature types in FEAT_TYPE order (unknown types last), each with its visible features. */
  let visible = $derived.by(() => {
    void langTick;
    const q = query.trim().toLowerCase();
    const order = toListOptions(featureTypes).map((o) => o.value);
    const types = [...new Set(features.map((f) => f.type || ""))].sort((a, b) => {
      const ia = order.indexOf(a), ib = order.indexOf(b);
      return (ia < 0 ? Infinity : ia) - (ib < 0 ? Infinity : ib) || a.localeCompare(b);
    });
    return types
      .map((type) => {
        const typeHit = q !== "" && (typeLabel(type).toLowerCase().includes(q) || type.toLowerCase().includes(q));
        const all = features.filter((f) => (f.type || "") === type);
        const shown = all.filter((f) => {
          const s = specs[f.code];
          if (view === "specified" && !s?.specified) return false;
          if (view === "missing" && s?.specified) return false;
          if (!q || typeHit) return true;
          return [f.name, f.code, f.description ?? ""].some((v) => v.toLowerCase().includes(q));
        });
        return { type, all, features: shown };
      })
      .filter((g) => g.features.length > 0);
  });

  /** "all" | "none" | "some" over the given features for one flag. */
  function groupState(codes: string[], flag: Flag) {
    const on = codes.filter((c) => specs[c]?.[flag]).length;
    return on === 0 ? "none" : on === codes.length ? "all" : "some";
  }

  // --- mutations -------------------------------------------------------------

  /** Next free order, in the seed's steps of 10. */
  function nextOrder() {
    const max = Object.values(specs).reduce((m, s) => (s.specified ? Math.max(m, Number(s.sort_order) || 0) : m), 0);
    return Math.floor(max / 10) * 10 + 10;
  }

  function setSpecified(code: string, value: boolean) {
    const s = specs[code];
    if (value && !s.specified) {
      // Re-ticking restores what was saved; a new feature gets the next order.
      const saved = initial[code];
      if (saved?.specified) Object.assign(s, $state.snapshot(saved));
      else s.sort_order = nextOrder();
    }
    s.specified = value;
    if (!value) s.required = s.copyable = false;
  }

  function setFlag(code: string, flag: Flag, value: boolean) {
    if (flag === "specified") return setSpecified(code, value);
    if (value) setSpecified(code, true);
    specs[code][flag] = value;
  }

  function setGroup(codes: string[], flag: Flag, value: boolean) {
    for (const c of codes) setFlag(c, flag, value);
  }

  // A search keeps every matching section open, so these act on the unfiltered list.
  let typeCodes = $derived([...new Set(features.map((f) => f.type || ""))]);
  let anyCollapsed = $derived(typeCodes.some((c) => collapsed[c]));
  let allCollapsed = $derived(typeCodes.length > 0 && typeCodes.every((c) => collapsed[c]));

  function setAllCollapsed(value: boolean) {
    collapsed = Object.fromEntries(typeCodes.map((c) => [c, value]));
  }

  function discard() {
    specs = $state.snapshot(initial);
  }

  async function save() {
    if (saving || changes === 0 || invalid) return;
    saving = true;
    const body: SpecificationMatrixEntry[] = Object.entries(specs)
      .filter(([, s]) => s.specified)
      .map(([feature, s]) => ({
        feature,
        default_value: s.default_value.trim() || null,
        required: s.required,
        copyable: s.copyable,
        sort_order: Number(s.sort_order) || 0,
      }));
    try {
      seed(await saveSpecificationMatrix(category, body));
      showToast(t("specification_matrix.saved", "Specifications saved"), "success");
    } catch (e) {
      showToast(apiErrorDetail(e, t("specification_matrix.save_error", "Could not save the specifications")), "error");
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
    if (categorySelect) categorySelect.value = category;
    leaveDialog?.close();
  }

  function confirmLeave() {
    const href = pendingHref;
    leaveDialog?.close();
    if (!href) return;
    // Drop the dirty state so the beforeunload guard does not ask again.
    initial = $state.snapshot(specs);
    window.location.href = href;
  }

  function switchCategory(code: string) {
    if (code !== category) leave(`/taxo/specifications?category=${encodeURIComponent(code)}`);
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
    if (category) load();
    // Type labels are only decoration: the sections still work without them.
    getListItemsbyList("FEAT_TYPE").then((items) => (featureTypes = items || [])).catch(() => {});
    // Categories are bounded configuration data; one generous page holds them all.
    getCategories(0, 1000)
      .then((rows) => {
        categories = categoryTree(rows || []);
        // Reached without `?category=`: open the first category.
        if (!category) {
          const first = categories[0]?.value;
          if (first) window.location.replace(`/taxo/specifications?category=${encodeURIComponent(first)}`);
          else (loading = false), (loadError = true);
        }
      })
      .catch(() => {
        if (!category) (loading = false), (loadError = true);
      });
    return () => {
      window.removeEventListener("languageChanged", onLang);
      window.removeEventListener("beforeunload", onUnload);
      document.removeEventListener("click", onLinkClick, true);
    };
  });

  const box = "h-4 w-4 shrink-0 cursor-pointer rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-600 dark:bg-gray-800";
  const field = "rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100";
  // In-row input: borderless until hovered or focused, so the table reads as a list.
  const cell = "w-full rounded-md border border-transparent bg-transparent px-2 py-1.5 text-sm text-gray-900 placeholder:text-gray-400 hover:border-gray-200 focus:border-indigo-500 focus:bg-white focus:outline-none disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-transparent dark:text-gray-100 dark:hover:border-gray-700 dark:focus:bg-gray-900";
  const bad = "!border-red-400 dark:!border-red-500";
  // Checkbox column cell: fixed width, divider on its left, full row height.
  const col = "flex w-20 shrink-0 items-center justify-center self-stretch border-l border-gray-200 sm:w-24 dark:border-gray-800";
  const head = "text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400";
  const ghost = "rounded-md p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-700 disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200";
  const chip = (on: boolean) =>
    `rounded-full px-3 py-1 text-xs font-medium transition ${on
      ? "bg-indigo-600 text-white"
      : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"}`;
  const FLAGS: { flag: Flag; key: string; fallback: string }[] = [
    { flag: "specified", key: "included", fallback: "Included" },
    { flag: "required", key: "required", fallback: "Required" },
    { flag: "copyable", key: "copyable", fallback: "Copyable" },
  ];
</script>

<div class="space-y-4">
  <!-- Category, summary and filters: a 2×2 grid on wide screens, so the
       category lines up with the search and the summary with the filters. -->
  <div class="grid gap-x-6 gap-y-3 rounded-xl border border-gray-200 bg-white p-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center dark:border-gray-800 dark:bg-white/[0.03]">
    <div class="flex min-w-0 items-center gap-3 lg:col-start-1 lg:row-start-1">
      <label for="sm-category" class="shrink-0 text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {t("specification_matrix.category", "Category")}
      </label>
      {#if categories.length}
        <select
          id="sm-category"
          bind:this={categorySelect}
          class="{field} min-w-0 flex-1 font-semibold sm:min-w-[14rem] sm:flex-none"
          value={category}
          onchange={(e) => switchCategory((e.currentTarget as HTMLSelectElement).value)}
        >
          {#each categories as c (c.value)}
            <option value={c.value}>{c.label}</option>
          {/each}
        </select>
      {:else}
        <p id="sm-category" class="text-lg font-semibold text-gray-900 dark:text-white">{categoryName || category}</p>
      {/if}
    </div>
    {#if !loading && !loadError}
      <p class="text-xs text-gray-500 lg:col-start-1 lg:row-start-2 dark:text-gray-400">
        <span class="font-semibold text-gray-900 dark:text-white">{totals.specified} / {totals.features}</span>
        {t("specification_matrix.summary_included", "features included")}
        <span class="mx-1.5 text-gray-300 dark:text-gray-600">·</span>
        <span class="font-semibold text-gray-900 dark:text-white">{totals.required}</span>
        {t("specification_matrix.summary_required", "required")}
        <span class="mx-1.5 text-gray-300 dark:text-gray-600">·</span>
        <span class="font-semibold text-gray-900 dark:text-white">{totals.copyable}</span>
        {t("specification_matrix.summary_copyable", "copyable")}
      </p>
      <input
        type="search"
        bind:value={query}
        placeholder={t("specification_matrix.search", "Search features…")}
        aria-label={t("specification_matrix.search", "Search features…")}
        class="{field} w-full lg:col-start-2 lg:row-start-1 lg:w-72"
      />
      <div class="flex flex-wrap items-center gap-2 lg:col-start-2 lg:row-start-2 lg:justify-end">
        <div class="flex flex-wrap gap-2" role="group" aria-label={t("specification_matrix.show", "Show")}>
          <button type="button" class={chip(view === "all")} aria-pressed={view === "all"} onclick={() => (view = "all")}>
            {t("specification_matrix.view_all", "All")}
          </button>
          <button type="button" class={chip(view === "specified")} aria-pressed={view === "specified"} onclick={() => (view = "specified")}>
            {t("specification_matrix.view_included", "Included")}
          </button>
          <button type="button" class={chip(view === "missing")} aria-pressed={view === "missing"} onclick={() => (view = "missing")}>
            {t("specification_matrix.view_missing", "Not included")}
          </button>
        </div>
        <!-- Expand / collapse every feature type: icon-only, name on hover. -->
        <span class="h-5 w-px bg-gray-200 dark:bg-gray-700" aria-hidden="true"></span>
        <div class="flex gap-0.5">
          <button
            type="button"
            class={ghost}
            onclick={() => setAllCollapsed(false)}
            disabled={query.trim() !== "" || !anyCollapsed}
            title={t("specification_matrix.expand_all", "Expand all")}
            aria-label={t("specification_matrix.expand_all", "Expand all")}
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
            title={t("specification_matrix.collapse_all", "Collapse all")}
            aria-label={t("specification_matrix.collapse_all", "Collapse all")}
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M6.24 3.2a.75.75 0 011.06.04L10 6.15l2.7-2.91a.75.75 0 111.1 1.02l-3.25 3.5a.75.75 0 01-1.1 0L6.2 4.26a.75.75 0 01.04-1.06zm3.21 9.04a.75.75 0 011.1 0l3.25 3.5a.75.75 0 11-1.1 1.02L10 13.85l-2.7 2.91a.75.75 0 11-1.1-1.02l3.25-3.5z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
    {/if}
  </div>

  {#if loading}
    <p class="py-10 text-center text-sm text-gray-500 dark:text-gray-400">{t("specification_matrix.loading", "Loading…")}</p>
  {:else if loadError}
    <div class="py-10 text-center">
      <button type="button" class="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400" onclick={() => (category ? load() : window.location.reload())}>
        {t("specification_matrix.retry", "Try again")}
      </button>
    </div>
  {:else}
    {#if visible.length === 0}
      <p class="rounded-xl border border-dashed border-gray-300 py-10 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
        {t("specification_matrix.empty", "No features match")}
      </p>
    {/if}

    {#each visible as g (g.type)}
      {@const codes = g.features.map((f) => f.code)}
      {@const open = !collapsed[g.type] || query.trim() !== ""}
      <section class="overflow-x-auto rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.03]">
        <div class="min-w-[52rem]">
          <header class="flex items-stretch border-b border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-white/[0.02]">
            <button
              type="button"
              class="flex min-w-0 flex-1 items-center gap-2 px-4 py-2.5 text-left"
              aria-expanded={open}
              onclick={() => (collapsed[g.type] = !collapsed[g.type])}
            >
              <svg class="h-4 w-4 shrink-0 text-gray-400 transition {open ? 'rotate-90' : ''}" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.17 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
              </svg>
              <span class="truncate text-sm font-semibold text-gray-900 dark:text-white">{typeLabel(g.type)}</span>
              <span class="shrink-0 rounded-full bg-gray-200 px-2 py-0.5 text-[11px] font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                {g.all.filter((f) => specs[f.code]?.specified).length}/{g.all.length}
              </span>
            </button>
            <span class="{head} flex w-20 shrink-0 items-center px-2">{t("specification_matrix.order", "Order")}</span>
            <span class="{head} flex w-56 shrink-0 items-center px-2">{t("specification_matrix.default_value", "Default value")}</span>
            {#each FLAGS as fl (fl.flag)}
              {@const st = groupState(codes, fl.flag)}
              <label class="{col} cursor-pointer flex-col gap-1 py-1.5">
                <span class={head}>{t(`specification_matrix.${fl.key}`, fl.fallback)}</span>
                <input
                  type="checkbox"
                  class={box}
                  checked={st === "all"}
                  use:indeterminate={st === "some"}
                  onchange={(e) => setGroup(codes, fl.flag, (e.currentTarget as HTMLInputElement).checked)}
                  aria-label={fmt(t(`specification_matrix.${fl.key}_all`, `${fl.fallback}: every feature in {type}`), { type: typeLabel(g.type) })}
                />
              </label>
            {/each}
          </header>

          {#if open}
            <ul class="divide-y divide-gray-100 dark:divide-gray-800">
              {#each g.features as f (f.code)}
                {@const s = specs[f.code]}
                {@const options = valueOptions(f, s.default_value)}
                <li class="flex items-stretch {changed(f.code) ? 'bg-amber-50 dark:bg-amber-500/10' : ''}">
                  <div class="flex min-w-0 flex-1 items-center gap-2 py-2 pl-10 pr-4">
                    {#if badOrder(f.code)}
                      <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-red-500" title={t("specification_matrix.error_order", "The order must be a whole number")}></span>
                    {:else if changed(f.code)}
                      <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" title={t("specification_matrix.unsaved", "Unsaved change")}></span>
                    {/if}
                    <div class="min-w-0">
                      <p class="truncate text-sm text-gray-900 dark:text-gray-100" title={f.description ?? ""}>{f.name}</p>
                      <p class="truncate font-mono text-[11px] text-gray-400 dark:text-gray-500">
                        {f.code}{#if f.list}<span class="ml-2" title={t("specification_matrix.list", "Values from the list")}>⋮ {f.list}</span>{/if}
                      </p>
                    </div>
                  </div>
                  <div class="flex w-20 shrink-0 items-center px-1">
                    <input
                      type="number"
                      step="1"
                      bind:value={s.sort_order}
                      disabled={!s.specified}
                      aria-label={fmt(t("specification_matrix.order_of", "Order of {feature}"), { feature: f.name })}
                      class="{cell} tabular-nums {badOrder(f.code) ? bad : ''}"
                    />
                  </div>
                  <div class="flex w-56 shrink-0 items-center px-1">
                    {#if options}
                      <select
                        bind:value={s.default_value}
                        disabled={!s.specified}
                        aria-label={fmt(t("specification_matrix.default_of", "Default value of {feature}"), { feature: f.name })}
                        class="{cell} pr-8"
                      >
                        <option value="">{t("specification_matrix.no_default", "— No default —")}</option>
                        {#each options as o (o.value)}
                          <option value={o.value}>{o.label}</option>
                        {/each}
                      </select>
                    {:else}
                      <input
                        bind:value={s.default_value}
                        disabled={!s.specified}
                        placeholder={s.specified ? t("specification_matrix.no_default_short", "No default") : ""}
                        aria-label={fmt(t("specification_matrix.default_of", "Default value of {feature}"), { feature: f.name })}
                        class="{cell} placeholder:italic"
                      />
                    {/if}
                  </div>
                  {#each FLAGS as fl (fl.flag)}
                    <div class={col}>
                      <input
                        type="checkbox"
                        class={box}
                        checked={s[fl.flag]}
                        onchange={(e) => setFlag(f.code, fl.flag, (e.currentTarget as HTMLInputElement).checked)}
                        aria-label={fmt(t(`specification_matrix.${fl.key}_one`, `${fl.fallback}: {feature}`), { feature: f.name })}
                      />
                    </div>
                  {/each}
                </li>
              {/each}
            </ul>
          {/if}
        </div>
      </section>
    {/each}
  {/if}

  <!-- Save bar: sticks to the bottom of the content column while there are changes. -->
  {#if changes > 0}
    <div class="sticky bottom-4 z-30 flex flex-col gap-3 rounded-xl border border-gray-200 bg-white/95 px-4 py-3 shadow-lg backdrop-blur sm:flex-row sm:items-center sm:justify-between dark:border-gray-800 dark:bg-gray-900/95">
      <p class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
        <span class="h-2 w-2 shrink-0 rounded-full {invalid ? 'bg-red-500' : 'bg-amber-500'}" aria-hidden="true"></span>
        {invalid
          ? t("specification_matrix.fix_errors", "Fix the rows marked in red before saving")
          : fmt(t("specification_matrix.pending", "{count} unsaved change(s)"), { count: changes })}
      </p>
      <div class="flex justify-end gap-3">
        <button type="button" class="rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-50 dark:text-gray-200 dark:hover:bg-gray-800" onclick={discard} disabled={saving}>
          {t("specification_matrix.discard", "Discard")}
        </button>
        <button type="button" class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50" onclick={save} disabled={saving || invalid}>
          {saving ? t("specification_matrix.saving", "Saving…") : t("specification_matrix.save", "Save specifications")}
        </button>
      </div>
    </div>
  {/if}
</div>

<!-- Same "Discard changes?" dialog as PrivilegeMatrix / AssetDetailModal. -->
<dialog
  bind:this={leaveDialog}
  oncancel={(e) => { e.preventDefault(); keepEditing(); }}
  class="rounded-2xl p-6 w-[420px] max-w-full bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100 backdrop:bg-black/60 backdrop:backdrop-blur-sm"
>
  <h3 class="text-base font-bold text-gray-900 dark:text-white">
    {t("specification_matrix.discard_title", "Discard changes?")}
  </h3>
  <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
    {t("specification_matrix.discard_message", "You have unsaved changes. If you leave now, they will be lost.")}
  </p>
  <div class="mt-5 flex justify-end gap-3">
    <button
      type="button"
      class="rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
      onclick={keepEditing}
    >
      {t("specification_matrix.discard_keep_editing", "Keep editing")}
    </button>
    <button
      type="button"
      class="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
      onclick={confirmLeave}
    >
      {t("specification_matrix.discard_confirm", "Discard changes")}
    </button>
  </div>
</dialog>
