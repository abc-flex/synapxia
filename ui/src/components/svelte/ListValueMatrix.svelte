<script lang="ts">
  /**
   * ListValueMatrix — `/admin/list_items?list=CODE` (without `?list=` it opens
   * the first list). Same layout as PrivilegeMatrix: a selector card on top, one
   * table below, a sticky save bar.
   *
   * One row per value and language: order, value and label, edited in place.
   * The language filter shows one language or all of them. The order belongs to
   * the value (the same in every language); a blank label removes that language;
   * the trash button removes the value in every language. Nothing is written until Save, which sends the whole set in one call
   * (`PUT /api/list_items/matrix/{list}`).
   *
   * Leaving with unsaved changes (list switch or any in-app link) asks through
   * the same "Discard changes?" dialog the detail modals use.
   */
  import { onMount, tick } from "svelte";
  import { getListItemsbyList, getListValueMatrix, saveListValueMatrix } from "@/lib/list_items";
  import { getLists } from "@/lib/lists";
  import { labelsByValue, listLabel, toListOptions } from "@/lib/listLang";
  import { apiErrorDetail } from "@/lib/api";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";
  import languagesData from "@/data/languages.json";
  import type { List, ListItem, ListValueMatrix } from "@/types/api";

  let { list }: { list: string } = $props();

  type Row = { id: number; value: string; sort_order: number; labels: Record<string, string>; isNew: boolean };
  type Saved = { sort_order: number; labels: Record<string, string> };

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

  const languageNames: Record<string, string> = Object.fromEntries(languagesData.map((l) => [l.code, l.label]));

  let listName = $state("");
  let lists = $state<List[]>([]);
  let listTypes = $state<ListItem[]>([]);
  let languages = $state<string[]>([]);
  let rows = $state<Row[]>([]);
  let initial = $state<Record<string, Saved>>({});
  let query = $state("");
  // "" = every language.
  let langFilter = $state("");
  let loading = $state(true);
  let loadError = $state(false);
  let saving = $state(false);

  let leaveDialog = $state<HTMLDialogElement | null>(null);
  // List picker: a listbox styled like the account menu (a native <select>
  // cannot show grey group titles or dividers).
  let pickerOpen = $state(false);
  let activeCode = $state("");
  let pickerEl = $state<HTMLDivElement | null>(null);
  let pickerPanel = $state<HTMLUListElement | null>(null);
  let pickerTrigger = $state<HTMLButtonElement | null>(null);
  let pendingHref: string | null = null;
  let nextId = 0;

  function seed(data: ListValueMatrix) {
    listName = data.list_name;
    // Every configured language gets a column, plus any other one already in use.
    languages = [...new Set([...languagesData.map((l) => l.code), ...data.languages])];
    rows = data.values.map((v) => ({ id: nextId++, value: v.value, sort_order: v.sort_order, labels: { ...v.labels }, isNew: false }));
    initial = Object.fromEntries(data.values.map((v) => [v.value, { sort_order: v.sort_order, labels: { ...v.labels } }]));
  }

  async function load() {
    loading = true;
    loadError = false;
    try {
      seed(await getListValueMatrix(list));
    } catch (e) {
      loadError = true;
      showToast(apiErrorDetail(e, t("list_value_matrix.load_error", "Could not load the list values")), "error");
    } finally {
      loading = false;
    }
  }

  const typeLabel = (type: string) => {
    void langTick;
    return listLabel(labelsByValue(listTypes), type) || type;
  };

  /** "Type: <name>", for the picker's group titles and the badge under it. */
  const typeTitle = (name: string) => fmt(t("list_value_matrix.type_title", "Type: {type}"), { type: name });

  /** The selector's lists grouped by type, in LIST_TYPE order (unknown types last). */
  let listGroups = $derived.by(() => {
    void langTick;
    const order = toListOptions(listTypes).map((o) => o.value);
    const types = [...new Set(lists.map((l) => l.type || ""))].sort((a, b) => {
      const ia = order.indexOf(a), ib = order.indexOf(b);
      return (ia < 0 ? Infinity : ia) - (ib < 0 ? Infinity : ib) || a.localeCompare(b);
    });
    return types.map((type) => ({
      type,
      label: type ? typeLabel(type) : t("list_value_matrix.no_type", "No type"),
      lists: lists.filter((l) => (l.type || "") === type),
    }));
  });
  let currentType = $derived(lists.find((l) => l.code === list)?.type ?? "");

  // --- derived views ---------------------------------------------------------

  const label = (r: Row, lang: string) => (r.labels[lang] ?? "").trim();
  const missing = (r: Row) => languages.some((l) => !label(r, l));

  /** One language row of a value: new, reordered or relabeled. */
  function langChanged(r: Row, lang: string): boolean {
    if (r.isNew) return true;
    const s = initial[r.value];
    if (!s) return true;
    return Number(r.sort_order) !== s.sort_order || label(r, lang) !== (s.labels[lang] ?? "");
  }

  function changed(r: Row): boolean {
    if (r.isNew) return true;
    const s = initial[r.value];
    if (!s) return true;
    if (Number(r.sort_order) !== s.sort_order) return true;
    return languages.some((l) => label(r, l) !== (s.labels[l] ?? ""));
  }

  let labelError = $derived(t("list_value_matrix.error_label", "Enter a label in at least one language"));

  /** Why a row cannot be saved, or "" when it can. */
  function problem(r: Row): string {
    const v = r.value.trim();
    if (!v) return t("list_value_matrix.error_value", "Enter the value's code");
    if (rows.some((o) => o !== r && o.value.trim() === v)) return t("list_value_matrix.error_duplicate", "This value is already in the list");
    if (languages.every((l) => !label(r, l))) return labelError;
    return "";
  }

  let removed = $derived(Object.keys(initial).filter((v) => !rows.some((r) => !r.isNew && r.value === v)).length);
  let changes = $derived(rows.filter(changed).length + removed);
  let invalid = $derived(rows.some((r) => problem(r) !== ""));
  let totals = $derived({ values: rows.length, missing: rows.filter(missing).length });

  let shownLangs = $derived(langFilter ? [langFilter] : languages);

  /** Each value with the language rows to show; a search matches the value or that row's label. */
  let visible = $derived.by(() => {
    const q = query.trim().toLowerCase();
    return rows
      .map((r) => ({
        row: r,
        langs: shownLangs.filter((l) =>
          r.isNew || !q || r.value.toLowerCase().includes(q) || label(r, l).toLowerCase().includes(q)),
      }))
      .filter((g) => g.langs.length > 0);
  });

  // --- mutations -------------------------------------------------------------

  function addValue() {
    const order = rows.reduce((m, r) => Math.max(m, Number(r.sort_order) || 0), 0) + 1;
    rows.push({ id: nextId++, value: "", sort_order: order, labels: {}, isNew: true });
    requestAnimationFrame(() => document.querySelector<HTMLInputElement>(`[data-new-value="${rows[rows.length - 1].id}"]`)?.focus());
  }

  function removeValue(r: Row) {
    rows = rows.filter((o) => o !== r);
  }

  function discard() {
    rows = Object.entries(initial)
      .map(([value, s]) => ({ id: nextId++, value, sort_order: s.sort_order, labels: { ...s.labels }, isNew: false }))
      .sort((a, b) => a.sort_order - b.sort_order || a.value.localeCompare(b.value));
  }

  async function save() {
    if (saving || changes === 0 || invalid) return;
    saving = true;
    const body = rows.map((r) => ({
      value: r.value.trim(),
      sort_order: Number(r.sort_order) || 0,
      labels: Object.fromEntries(languages.map((l) => [l, label(r, l)]).filter(([, v]) => v)),
    }));
    try {
      seed(await saveListValueMatrix(list, body));
      showToast(t("list_value_matrix.saved", "List values saved"), "success");
    } catch (e) {
      showToast(apiErrorDetail(e, t("list_value_matrix.save_error", "Could not save the list values")), "error");
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
    leaveDialog?.close();
  }

  function confirmLeave() {
    const href = pendingHref;
    leaveDialog?.close();
    if (!href) return;
    // Drop the dirty state so the beforeunload guard does not ask again.
    discard();
    window.location.href = href;
  }

  function switchList(code: string) {
    if (code !== list) leave(`/admin/list_items?list=${encodeURIComponent(code)}`);
  }

  // --- list picker ------------------------------------------------------------

  let flatLists = $derived(listGroups.flatMap((g) => g.lists));
  let currentListName = $derived(lists.find((l) => l.code === list)?.name || listName || list);

  async function openPicker() {
    pickerOpen = true;
    activeCode = list || flatLists[0]?.code || "";
    await tick();
    pickerPanel?.focus();
    revealActive("center");
  }

  function closePicker(refocus = true) {
    pickerOpen = false;
    if (refocus) pickerTrigger?.focus();
  }

  function pick(code: string) {
    closePicker();
    switchList(code);
  }

  function revealActive(block: ScrollLogicalPosition = "nearest") {
    document.getElementById(`lvm-opt-${activeCode}`)?.scrollIntoView({ block });
  }

  function onPickerKey(e: KeyboardEvent) {
    const i = flatLists.findIndex((l) => l.code === activeCode);
    const move = (to: number) => {
      e.preventDefault();
      activeCode = flatLists[Math.max(0, Math.min(flatLists.length - 1, to))]?.code ?? activeCode;
      tick().then(() => revealActive());
    };
    if (e.key === "ArrowDown") move(i + 1);
    else if (e.key === "ArrowUp") move(i - 1);
    else if (e.key === "Home") move(0);
    else if (e.key === "End") move(flatLists.length - 1);
    else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (activeCode) pick(activeCode);
    } else if (e.key === "Escape" || e.key === "Tab") {
      if (e.key === "Escape") e.preventDefault();
      closePicker(e.key === "Escape");
    }
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
    const onOutside = (e: MouseEvent) => {
      if (pickerOpen && pickerEl && !pickerEl.contains(e.target as Node)) closePicker(false);
    };
    window.addEventListener("languageChanged", onLang);
    document.addEventListener("mousedown", onOutside);
    window.addEventListener("beforeunload", onUnload);
    document.addEventListener("click", onLinkClick, true);
    if (list) load();
    // Type labels are only decoration: the selector still works without them.
    getListItemsbyList("LIST_TYPE").then((items) => (listTypes = items || [])).catch(() => {});
    // Lists are bounded configuration data; one generous page holds them all.
    getLists(0, 1000)
      .then((l) => {
        lists = l || [];
        // Reached without `?list=`: open the first list.
        if (!list) {
          const first = listGroups[0]?.lists[0]?.code;
          if (first) window.location.replace(`/admin/list_items?list=${encodeURIComponent(first)}`);
          else (loading = false), (loadError = true);
        }
      })
      .catch(() => {
        if (!list) (loading = false), (loadError = true);
      });
    return () => {
      window.removeEventListener("languageChanged", onLang);
      window.removeEventListener("beforeunload", onUnload);
      document.removeEventListener("click", onLinkClick, true);
      document.removeEventListener("mousedown", onOutside);
    };
  });

  const field = "rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100";
  // In-row input: borderless until hovered or focused, so the table reads as a list.
  const cell = "w-full rounded-md border border-transparent bg-transparent px-2 py-1.5 text-sm text-gray-900 placeholder:text-gray-400 hover:border-gray-200 focus:border-indigo-500 focus:bg-white focus:outline-none dark:text-gray-100 dark:hover:border-gray-700 dark:focus:bg-gray-900";
  const bad = "!border-red-400 dark:!border-red-500";
  const ghost = "rounded-md p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-700 disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200";
  const head = "text-[11px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400";
</script>

<div class="space-y-4">
  <!-- List, summary and filters: a 2×2 grid on wide screens, so the picker lines
       up with the search and the summary with the filters. -->
  <div class="grid gap-x-6 gap-y-3 rounded-xl border border-gray-200 bg-white p-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center dark:border-gray-800 dark:bg-white/[0.03]">
    <div class="flex min-w-0 items-center gap-3 lg:col-start-1 lg:row-start-1">
      <label for="lvm-list" id="lvm-list-label" class="shrink-0 text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {t("list_value_matrix.list", "List")}
      </label>
      {#if lists.length}
        <div class="relative min-w-0 flex-1 sm:flex-none" bind:this={pickerEl}>
          <button
            id="lvm-list"
            type="button"
            bind:this={pickerTrigger}
            class="{field} flex w-full min-w-[14rem] items-center justify-between gap-3 text-left font-semibold sm:w-auto"
            aria-haspopup="listbox"
            aria-expanded={pickerOpen}
            aria-labelledby="lvm-list-label lvm-list"
            onclick={() => (pickerOpen ? closePicker() : openPicker())}
            onkeydown={(e) => {
              if (!pickerOpen && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
                e.preventDefault();
                openPicker();
              }
            }}
          >
            <span class="truncate">{currentListName}</span>
            <svg class="h-4 w-4 shrink-0 text-gray-500 transition duration-200 dark:text-gray-400 {pickerOpen ? 'rotate-180' : ''}" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
            </svg>
          </button>

          {#if pickerOpen}
            <!-- Same look as the account menu: grey group titles, dividers between groups. -->
            <ul
              bind:this={pickerPanel}
              role="listbox"
              tabindex="-1"
              aria-labelledby="lvm-list-label"
              aria-activedescendant={activeCode ? `lvm-opt-${activeCode}` : undefined}
              onkeydown={onPickerKey}
              class="absolute left-0 z-40 mt-2 max-h-[26rem] w-full min-w-[18rem] overflow-y-auto rounded-2xl border border-gray-200 bg-white p-3 shadow-lg focus:outline-none sm:w-80 dark:border-gray-800 dark:bg-gray-900"
            >
              {#each listGroups as g, gi (g.type)}
                <li role="presentation" class={gi > 0 ? "mt-2 border-t border-gray-200 pt-3 dark:border-gray-800" : ""}>
                  <span class="mb-1 block px-3 text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500" aria-hidden="true">
                    {typeTitle(g.label)}
                  </span>
                  <ul role="group" aria-label={g.label} class="flex flex-col gap-0.5">
                    {#each g.lists as l (l.code)}
                      {@const selected = l.code === list}
                      <!-- Keys are handled by the listbox (aria-activedescendant), not per option. -->
                      <!-- svelte-ignore a11y_click_events_have_key_events -->
                      <li
                        id="lvm-opt-{l.code}"
                        role="option"
                        aria-selected={selected}
                        class="flex cursor-pointer items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm font-normal
                          {selected ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-700 dark:text-gray-400'}
                          {l.code === activeCode ? 'bg-gray-100 dark:bg-white/5' : 'hover:bg-gray-100 dark:hover:bg-white/5'}"
                        onclick={() => pick(l.code)}
                        onmousemove={() => (activeCode = l.code)}
                      >
                        <span class="truncate">{l.name}</span>
                        {#if selected}
                          <svg class="h-4 w-4 shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                            <path fill-rule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clip-rule="evenodd" />
                          </svg>
                        {/if}
                      </li>
                    {/each}
                  </ul>
                </li>
              {/each}
            </ul>
          {/if}
        </div>
      {:else}
        <p id="lvm-list" class="text-lg font-semibold text-gray-900 dark:text-white">{listName || list}</p>
      {/if}
    </div>
    {#if !loading && !loadError}
      <p class="flex flex-wrap items-center text-xs text-gray-500 lg:col-start-1 lg:row-start-2 dark:text-gray-400">
        {#if currentType}
          <span class="mr-2 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300" title={t("list_value_matrix.type", "List type")}>
            {typeTitle(typeLabel(currentType))}
          </span>
        {/if}
        <span class="mr-1 font-semibold text-gray-900 dark:text-white">{totals.values}</span>
        {t("list_value_matrix.summary_values", "values")}
        <span class="mx-1.5 text-gray-300 dark:text-gray-600">·</span>
        <span class="mr-1 font-semibold text-gray-900 dark:text-white">{totals.missing}</span>
        {t("list_value_matrix.summary_missing", "missing a translation")}
      </p>
      <input
        type="search"
        bind:value={query}
        placeholder={t("list_value_matrix.search", "Search values…")}
        aria-label={t("list_value_matrix.search", "Search values…")}
        class="{field} w-full lg:col-start-2 lg:row-start-1 lg:w-72"
      />
      <div class="flex flex-wrap items-center gap-2 lg:col-start-2 lg:row-start-2 lg:justify-end">
        <select
          bind:value={langFilter}
          aria-label={t("list_value_matrix.language", "Language")}
          class="rounded-md border border-gray-300 bg-white py-1 pl-2 pr-8 text-xs text-gray-700 focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200"
        >
          <option value="">{t("list_value_matrix.all_languages", "All languages")}</option>
          {#each languages as lang (lang)}
            <option value={lang}>{languageNames[lang] ?? lang}</option>
          {/each}
        </select>
        <span class="h-5 w-px bg-gray-200 dark:bg-gray-700" aria-hidden="true"></span>
        <button
          type="button"
          class="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-500/10"
          onclick={addValue}
        >
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
          </svg>
          {t("list_value_matrix.add", "New value")}
        </button>
      </div>
    {/if}
  </div>

  {#if loading}
    <p class="py-10 text-center text-sm text-gray-500 dark:text-gray-400">{t("list_value_matrix.loading", "Loading…")}</p>
  {:else if loadError}
    <div class="py-10 text-center">
      <button type="button" class="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400" onclick={() => (list ? load() : window.location.reload())}>
        {t("list_value_matrix.retry", "Try again")}
      </button>
    </div>
  {:else if visible.length === 0}
    <p class="rounded-xl border border-dashed border-gray-300 py-10 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
      {rows.length === 0 ? t("list_value_matrix.empty_list", "This list has no values yet") : t("list_value_matrix.empty", "No values match")}
    </p>
  {:else}
    <section class="overflow-x-auto rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.03]">
      <div class="min-w-[36rem]">
        <header class="flex items-center gap-2 border-b border-gray-200 bg-gray-50 px-4 py-2.5 dark:border-gray-800 dark:bg-white/[0.02]">
          <span class="w-3 shrink-0" aria-hidden="true"></span>
          <span class="{head} w-20 shrink-0 px-2">{t("list_value_matrix.order", "Order")}</span>
          <span class="{head} w-52 shrink-0 px-2">{t("list_value_matrix.value", "Value")}</span>
          <span class="{head} min-w-0 flex-1 px-2">{t("list_value_matrix.label", "Label")}</span>
          <span class="w-8 shrink-0" aria-hidden="true"></span>
        </header>

        <!-- One block per value (dividers between values), one row per language inside. -->
        <ul class="divide-y divide-gray-100 dark:divide-gray-800">
          {#each visible as g (g.row.id)}
            {@const r = g.row}
            {@const err = problem(r)}
            <li class="py-1">
              {#each g.langs as lang (lang)}
                {@const dirty = langChanged(r, lang)}
                <div class="flex items-center gap-2 px-4 py-0.5 {dirty ? 'bg-amber-50 dark:bg-amber-500/10' : ''}">
                  <span class="flex w-3 shrink-0 justify-center">
                    {#if err}
                      <span class="h-1.5 w-1.5 rounded-full bg-red-500" title={err}></span>
                    {:else if dirty}
                      <span class="h-1.5 w-1.5 rounded-full bg-amber-500" title={t("list_value_matrix.unsaved", "Unsaved change")}></span>
                    {/if}
                  </span>
                  <div class="w-20 shrink-0">
                    <input
                      type="number"
                      bind:value={r.sort_order}
                      title={t("list_value_matrix.order_hint", "The order applies to every language")}
                      aria-label={fmt(t("list_value_matrix.order_of", "Order of {value}"), { value: r.value })}
                      class="{cell} tabular-nums"
                    />
                  </div>
                  <div class="w-52 shrink-0">
                    {#if r.isNew}
                      <input
                        data-new-value={r.id}
                        bind:value={r.value}
                        maxlength="100"
                        placeholder={t("list_value_matrix.value_placeholder", "e.g. IN_PROGRESS")}
                        aria-label={t("list_value_matrix.value", "Value")}
                        title={err}
                        class="{cell} font-mono {err && err !== labelError ? bad : '!border-gray-300 dark:!border-gray-600'}"
                      />
                    {:else}
                      <p class="truncate px-2 font-mono text-xs text-gray-600 dark:text-gray-300" title={r.value}>{r.value}</p>
                    {/if}
                  </div>
                  <div class="flex min-w-0 flex-1 items-center gap-2">
                    {#if !langFilter}
                      <span class="w-7 shrink-0 rounded bg-gray-100 py-0.5 text-center font-mono text-[11px] uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400" title={languageNames[lang] ?? lang}>{lang}</span>
                    {/if}
                    <input
                      value={r.labels[lang] ?? ""}
                      oninput={(e) => (r.labels[lang] = (e.currentTarget as HTMLInputElement).value)}
                      maxlength="200"
                      placeholder={t("list_value_matrix.missing", "Missing")}
                      aria-label={fmt(t("list_value_matrix.label_of", "{language} label of {value}"), { language: languageNames[lang] ?? lang, value: r.value })}
                      class="{cell} placeholder:italic"
                    />
                  </div>
                  <div class="flex w-8 shrink-0 justify-center">
                    <button
                      type="button"
                      class="{ghost} hover:!text-red-600 dark:hover:!text-red-400"
                      onclick={() => removeValue(r)}
                      title={t("list_value_matrix.remove", "Remove value")}
                      aria-label={fmt(t("list_value_matrix.remove_one", "Remove {value}"), { value: r.value })}
                    >
                      <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fill-rule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clip-rule="evenodd" />
                      </svg>
                    </button>
                  </div>
                </div>
              {/each}
            </li>
          {/each}
        </ul>
      </div>
    </section>
  {/if}

  <!-- Save bar: sticks to the bottom of the content column while there are changes. -->
  {#if changes > 0}
    <div class="sticky bottom-4 z-30 flex flex-col gap-3 rounded-xl border border-gray-200 bg-white/95 px-4 py-3 shadow-lg backdrop-blur sm:flex-row sm:items-center sm:justify-between dark:border-gray-800 dark:bg-gray-900/95">
      <p class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
        <span class="h-2 w-2 shrink-0 rounded-full {invalid ? 'bg-red-500' : 'bg-amber-500'}" aria-hidden="true"></span>
        {invalid
          ? t("list_value_matrix.fix_errors", "Fix the rows marked in red before saving")
          : fmt(t("list_value_matrix.pending", "{count} unsaved change(s)"), { count: changes })}
      </p>
      <div class="flex justify-end gap-3">
        <button type="button" class="rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-50 dark:text-gray-200 dark:hover:bg-gray-800" onclick={discard} disabled={saving}>
          {t("list_value_matrix.discard", "Discard")}
        </button>
        <button type="button" class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50" onclick={save} disabled={saving || invalid}>
          {saving ? t("list_value_matrix.saving", "Saving…") : t("list_value_matrix.save", "Save values")}
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
    {t("list_value_matrix.discard_title", "Discard changes?")}
  </h3>
  <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
    {t("list_value_matrix.discard_message", "You have unsaved changes. If you leave now, they will be lost.")}
  </p>
  <div class="mt-5 flex justify-end gap-3">
    <button
      type="button"
      class="rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
      onclick={keepEditing}
    >
      {t("list_value_matrix.discard_keep_editing", "Keep editing")}
    </button>
    <button
      type="button"
      class="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
      onclick={confirmLeave}
    >
      {t("list_value_matrix.discard_confirm", "Discard changes")}
    </button>
  </div>
</dialog>
