<script lang="ts">
  /**
   * DashboardRun — the Dashboard Catalog's Execute flow
   * (specs/007-dashboard-catalog US2/US3, research R4/R8/R10).
   *
   * Listens for any `[data-action="execute"]` click (cards and the detail),
   * loads the run form (parameters already resolved for this viewer), shows
   * the parameters window, validates, then starts the run on the server and
   * opens the dashboard:
   *   - TAB (external BI): a blank tab is opened synchronously in the click,
   *     then pointed at the launch URL — so popup blockers let it through.
   *     Blocked → FAILED + a manual link.
   *   - VIEWER (Internal Page): a same-origin iframe in the viewer dialog.
   *     load → SUCCESS · 30 s → TIMEOUT · closed before load → CANCELLED.
   * Closing the parameters window without running records CANCELLED.
   * Every finish call fires at most once per execution.
   */
  import { onMount } from "svelte";
  import { apiErrorDetail } from "@/lib/api";
  import {
    finishExecution,
    getLastValues,
    getRunForm,
    recordCancelled,
    startExecution,
  } from "@/lib/dashboardExecutions";
  import { inputClass, labelClass } from "@/lib/formClasses";
  import { toListOptions } from "@/lib/listLang";
  import { showToast } from "@/lib/toast";
  import { translate } from "@/utils/i18nClient";
  import type { ExecutionStarted, RunForm, RunFormParameter } from "@/types/api";

  const TIMEOUT_MS = 30_000;
  const MAX_LEN = 1000;
  const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

  // ── i18n ──────────────────────────────────────────────────────────────
  let langTick = $state(0);
  const t = (key: string, fallback: string): string => {
    void langTick;
    const v = translate(`dashboard_catalog.${key}`);
    return v && v !== `dashboard_catalog.${key}` ? v : fallback;
  };
  const lang = (): string => {
    void langTick;
    return (typeof localStorage !== "undefined" && localStorage.getItem("lang")) === "es" ? "es" : "en";
  };

  // ── Parameters window state ───────────────────────────────────────────
  let winEl: HTMLDialogElement | undefined = $state();
  let dashId = $state(0);
  let dashName = $state("");
  let form: RunForm | null = $state(null);
  let loading = $state(false);
  let loadError = $state("");
  let values: Record<string, string> = $state({});
  let errors: Record<string, string> = $state({});
  let banner = $state("");
  let running = $state(false);
  let openedAt = 0;
  let resolved = false; // set once the window ends in a run (no CANCELLED record)

  const asked = $derived((form?.parameters ?? []).filter((p) => p.effective_source !== "GRANT"));
  const bound = $derived((form?.parameters ?? []).filter((p) => p.effective_source === "GRANT"));

  // ── Viewer / outcome state ────────────────────────────────────────────
  type ViewerState = "loading" | "loaded" | "timeout" | "error" | "blocked";
  let viewerEl: HTMLDialogElement | undefined = $state();
  let viewer: {
    execId: number;
    name: string;
    url: string;
    fullUrl: string;
    used: { label: string; value: string }[];
    state: ViewerState;
  } | null = $state(null);
  let timer: ReturnType<typeof setTimeout> | null = null;
  const finished = new Set<number>();

  function finishOnce(execId: number, status: "SUCCESS" | "FAILED" | "TIMEOUT" | "CANCELLED", message?: string) {
    if (finished.has(execId)) return;
    finished.add(execId);
    // Best effort: a late or duplicate report answers 409 and is ignored.
    finishExecution(execId, status, message).catch(() => {});
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  function optionsFor(p: RunFormParameter) {
    void langTick;
    return toListOptions(p.options ?? [], lang());
  }

  function displayValue(p: RunFormParameter, value: string): string {
    if (p.effective_source === "LIST") {
      return optionsFor(p).find((o) => o.value === value)?.label ?? value;
    }
    if (p.data_type === "BOOLEAN") {
      return value === "true" ? t("bool_true", "Yes") : value === "false" ? t("bool_false", "No") : value;
    }
    return value;
  }

  function problem(p: RunFormParameter, raw: string): string {
    const v = (raw ?? "").trim();
    if (p.effective_source === "LIST" && p.list_unavailable) {
      return p.is_required ? t("err_list_unavailable", "This list has no values, so the dashboard cannot be run.") : "";
    }
    if (!v) return p.is_required ? t("err_required", "This value is required.") : "";
    if (v.length > MAX_LEN) return t("err_too_long", "At most 1000 characters.");
    if (p.effective_source === "LIST") {
      return (p.options ?? []).some((o) => o.value === v) ? "" : t("err_list", "Choose one of the values.");
    }
    if (p.data_type === "NUMBER" && !Number.isFinite(Number(v))) return t("err_number", "Enter a number.");
    if (p.data_type === "DATE") {
      const d = new Date(`${v}T00:00:00Z`);
      if (!DATE_RE.test(v) || Number.isNaN(d.getTime()) || d.toISOString().slice(0, 10) !== v) {
        return t("err_date", "Enter a valid date.");
      }
    }
    if (p.data_type === "BOOLEAN" && v !== "true" && v !== "false") return t("err_required", "This value is required.");
    return "";
  }

  function validate(): boolean {
    const next: Record<string, string> = {};
    for (const p of asked) {
      const msg = problem(p, values[p.name] ?? "");
      if (msg) next[p.name] = msg;
    }
    errors = next;
    return Object.keys(next).length === 0;
  }

  /** The viewer-supplied values (never the grant-bound ones — the server sets those). */
  function submitted(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const p of asked) {
      const v = (values[p.name] ?? "").trim();
      if (v) out[p.name] = v;
    }
    return out;
  }

  // ── Open ──────────────────────────────────────────────────────────────
  async function openFor(id: number, name: string, tab: Window | null) {
    dashId = id;
    dashName = name;
    form = null;
    values = {};
    errors = {};
    banner = "";
    loadError = "";
    resolved = false;
    loading = true;
    try {
      const f = await getRunForm(id);
      form = f;
      dashName = f.name || name;
      const initial: Record<string, string> = {};
      for (const p of f.parameters) {
        if (p.effective_source !== "GRANT") initial[p.name] = p.default_value ?? "";
      }
      values = initial;
    } catch (err) {
      tab?.close();
      showToast(apiErrorDetail(err, t("load_error", "Could not load this dashboard's parameters.")), "error");
      loading = false;
      return;
    }
    loading = false;
    if (asked.length === 0) {
      // Nothing to ask (no parameters, or every one fixed by the viewer's grant).
      void run(tab);
      return;
    }
    tab?.close(); // the window needs input first; Execute will open a fresh tab
    openedAt = performance.now();
    winEl?.showModal();
  }

  function onExecuteClick(e: MouseEvent) {
    const btn = (e.target as HTMLElement).closest?.('[data-action="execute"]') as HTMLElement | null;
    if (!btn || btn.closest("[data-dashboard-run]")) return;
    const id = Number(btn.dataset.dashboardId);
    if (!id) return;
    e.preventDefault();
    // An external dashboard with no parameters runs straight away, after the
    // run-form request — too late for the click's user activation. Pre-open
    // its tab now (only then, so a window that needs input never flashes one).
    const preTab = btn.dataset.mode === "TAB" && btn.dataset.paramCount === "0"
      ? window.open("", "_blank")
      : null;
    void openFor(id, btn.dataset.dashboardName ?? "", preTab);
  }

  // ── Run ───────────────────────────────────────────────────────────────
  async function run(preTab: Window | null = null) {
    if (!form || running) return;
    if (!validate()) return;
    const isTab = form.mode === "TAB";
    // Open the tab synchronously inside the click (popup blockers allow it).
    const tab = isTab ? preTab ?? window.open("", "_blank") : null;
    running = true;
    banner = "";
    let started: ExecutionStarted;
    try {
      started = await startExecution(dashId, submitted());
    } catch (err) {
      tab?.close();
      running = false;
      const msg = apiErrorDetail(err, t("run_refused", "This dashboard could not be run."));
      if (winEl?.open) banner = msg;
      else showToast(msg, "error");
      return;
    }
    running = false;
    resolved = true;
    const used = (form.parameters ?? [])
      .map((p) => {
        const v = p.effective_source === "GRANT" ? p.bound_value ?? "" : (values[p.name] ?? "").trim() || (p.default_value ?? "");
        return { label: p.label, value: v ? displayValue(p, v) : "" };
      })
      .filter((u) => u.value);
    if (winEl?.open) winEl.close();

    if (started.mode === "TAB") {
      if (tab) {
        try {
          tab.opener = null;
          tab.location.href = started.launch_url;
          finishOnce(started.execution_id, "SUCCESS");
        } catch {
          finishOnce(started.execution_id, "FAILED", "The new tab could not be opened");
        }
      } else {
        finishOnce(started.execution_id, "FAILED", "Popup blocked");
        viewer = { execId: started.execution_id, name: dashName, url: started.launch_url, fullUrl: started.launch_url, used, state: "blocked" };
        viewerEl?.showModal();
      }
      return;
    }

    const full = new URL(started.launch_url, window.location.origin);
    full.searchParams.delete("embed");
    viewer = {
      execId: started.execution_id,
      name: dashName,
      url: started.launch_url,
      fullUrl: full.pathname + full.search,
      used,
      state: "loading",
    };
    viewerEl?.showModal();
    clearTimer();
    timer = setTimeout(() => {
      if (viewer && viewer.state === "loading") {
        viewer.state = "timeout";
        finishOnce(viewer.execId, "TIMEOUT", "Did not load within 30 s");
      }
    }, TIMEOUT_MS);
  }

  function clearTimer() {
    if (timer) clearTimeout(timer);
    timer = null;
  }

  function onFrameLoad() {
    if (!viewer || viewer.state !== "loading") return; // a late load after TIMEOUT changes nothing
    clearTimer();
    viewer.state = "loaded";
    finishOnce(viewer.execId, "SUCCESS");
  }

  function onFrameError() {
    if (!viewer || viewer.state !== "loading") return;
    clearTimer();
    viewer.state = "error";
    finishOnce(viewer.execId, "FAILED", "The dashboard could not be loaded");
  }

  // ── Close ─────────────────────────────────────────────────────────────
  function onWindowClose() {
    if (resolved || !dashId || !form) return;
    resolved = true;
    // Abandoned window → CANCELLED with the values it held (best effort).
    recordCancelled(dashId, submitted(), performance.now() - openedAt).catch(() => {});
  }

  function onViewerClose() {
    clearTimer();
    if (viewer && viewer.state === "loading") finishOnce(viewer.execId, "CANCELLED");
    viewer = null;
  }

  async function useLast() {
    try {
      const last = await getLastValues(dashId);
      const names = new Set(asked.map((p) => p.name));
      const picked = Object.entries(last.values ?? {}).filter(([k]) => names.has(k));
      if (!picked.length) {
        showToast(t("last_none", "No previous values could be used."), "info");
        return;
      }
      values = { ...values, ...Object.fromEntries(picked) };
      errors = {};
    } catch (err) {
      showToast(apiErrorDetail(err, t("last_none", "No previous values could be used.")), "error");
    }
  }

  onMount(() => {
    const onLang = () => (langTick += 1);
    document.addEventListener("click", onExecuteClick);
    window.addEventListener("languageChanged", onLang);
    return () => {
      document.removeEventListener("click", onExecuteClick);
      window.removeEventListener("languageChanged", onLang);
      clearTimer();
    };
  });

  const fieldId = (p: RunFormParameter) => `dash-run-${p.name}`;
</script>

<!-- Parameters window -->
<dialog
  bind:this={winEl}
  data-dashboard-run
  onclose={onWindowClose}
  class="m-auto w-[min(560px,calc(100vw-2rem))] max-h-[calc(100vh-2rem)] overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 text-gray-900 shadow-xl backdrop:bg-gray-900/50 dark:border-gray-800 dark:bg-gray-900 dark:text-white"
>
  <form
    method="dialog"
    class="flex max-h-[calc(100vh-2rem)] flex-col"
    onsubmit={(e) => { e.preventDefault(); void run(); }}
    novalidate
  >
    <header class="border-b border-gray-100 px-5 py-4 dark:border-gray-800">
      <h2 class="text-lg font-semibold">{t("window_title", "Run parameters")}</h2>
      <p class="mt-0.5 truncate text-sm text-gray-500 dark:text-gray-400">{dashName}</p>
    </header>

    <div class="flex-1 space-y-4 overflow-y-auto px-5 py-4">
      {#if loading}
        <p class="text-sm text-gray-500">{t("loading", "Loading…")}</p>
      {:else if loadError}
        <p class="text-sm text-red-600 dark:text-red-400">{loadError}</p>
      {:else if form}
        <p class="text-sm text-gray-500 dark:text-gray-400">{t("window_hint", "Fill in the values and press Execute.")}</p>

        {#if banner}
          <div role="alert" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">{banner}</div>
        {/if}

        {#each bound as p (p.name)}
          <div>
            <label class={labelClass} for={fieldId(p)}>{p.label}</label>
            <input id={fieldId(p)} class={`${inputClass} !bg-gray-100 dark:!bg-gray-800`} value={p.bound_value ?? ""} readonly aria-readonly="true" />
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{t("bound_hint", "Set by how this dashboard was shared with you")}</p>
          </div>
        {/each}

        {#each asked as p (p.name)}
          <div>
            <label class={labelClass} for={fieldId(p)}>
              {p.label}
              {#if p.is_required}<span class="text-red-500" title={t("required_mark", "Required")}> *</span>{/if}
            </label>

            {#if p.effective_source === "LIST"}
              <select id={fieldId(p)} class={inputClass} bind:value={values[p.name]} disabled={p.list_unavailable} aria-invalid={errors[p.name] ? "true" : "false"}>
                <option value="">{t("choose", "— choose —")}</option>
                {#each optionsFor(p) as o (o.value)}
                  <option value={o.value}>{o.label}</option>
                {/each}
              </select>
            {:else if p.data_type === "BOOLEAN"}
              <select id={fieldId(p)} class={inputClass} bind:value={values[p.name]} aria-invalid={errors[p.name] ? "true" : "false"}>
                <option value="">{p.is_required ? t("choose", "— choose —") : t("not_set", "Not set")}</option>
                <option value="true">{t("bool_true", "Yes")}</option>
                <option value="false">{t("bool_false", "No")}</option>
              </select>
            {:else if p.data_type === "NUMBER"}
              <input id={fieldId(p)} type="number" step="any" class={inputClass} bind:value={values[p.name]} aria-invalid={errors[p.name] ? "true" : "false"} />
            {:else if p.data_type === "DATE"}
              <input id={fieldId(p)} type="date" class={inputClass} bind:value={values[p.name]} aria-invalid={errors[p.name] ? "true" : "false"} />
            {:else}
              <input id={fieldId(p)} type="text" maxlength={MAX_LEN} class={inputClass} bind:value={values[p.name]} aria-invalid={errors[p.name] ? "true" : "false"} />
            {/if}

            {#if p.effective_source === "LIST" && p.list_unavailable}
              <p class="mt-1 text-xs text-amber-600 dark:text-amber-400">{t("err_list_unavailable", "This list has no values, so the dashboard cannot be run.")}</p>
            {/if}
            {#if errors[p.name]}
              <p class="mt-1 text-xs text-red-600 dark:text-red-400">{errors[p.name]}</p>
            {/if}
          </div>
        {/each}
      {/if}
    </div>

    <footer class="flex flex-wrap items-center justify-between gap-2 border-t border-gray-100 px-5 py-3 dark:border-gray-800">
      <div>
        {#if form?.has_last_values}
          <button type="button" onclick={useLast} class="rounded-lg px-3 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50 dark:text-indigo-300 dark:hover:bg-indigo-500/10">
            {t("use_last", "Use my last values")}
          </button>
        {/if}
      </div>
      <div class="flex gap-2">
        <button type="button" onclick={() => winEl?.close()} class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800">
          {t("cancel", "Cancel")}
        </button>
        <button type="submit" disabled={running || loading || !form} class="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60">
          {running ? t("running", "Opening…") : t("execute", "Execute")}
        </button>
      </div>
    </footer>
  </form>
</dialog>

<!-- Viewer (Internal Page) / popup-blocked notice -->
<dialog
  bind:this={viewerEl}
  data-dashboard-run
  onclose={onViewerClose}
  class={`m-auto overflow-hidden rounded-2xl border border-gray-200 bg-white p-0 text-gray-900 shadow-xl backdrop:bg-gray-900/50 dark:border-gray-800 dark:bg-gray-900 dark:text-white ${viewer?.state === "blocked" ? "w-[min(480px,calc(100vw-2rem))]" : "h-[calc(100vh-2rem)] w-[calc(100vw-2rem)] max-w-[1400px]"}`}
>
  {#if viewer}
    <div class="flex h-full flex-col">
      <header class="flex flex-wrap items-start justify-between gap-3 border-b border-gray-100 px-4 py-3 dark:border-gray-800">
        <div class="min-w-0">
          <h2 class="truncate text-base font-semibold">{viewer.name}</h2>
          {#if viewer.used.length && viewer.state !== "blocked"}
            <p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
              <span class="font-medium">{t("viewer_values", "Values used")}:</span>
              {viewer.used.map((u) => `${u.label}: ${u.value}`).join(" · ")}
            </p>
          {/if}
        </div>
        <div class="flex shrink-0 items-center gap-2">
          {#if viewer.state !== "blocked"}
            <a href={viewer.fullUrl} target="_blank" rel="noopener" class="rounded-lg px-3 py-1.5 text-sm font-medium text-indigo-600 hover:bg-indigo-50 dark:text-indigo-300 dark:hover:bg-indigo-500/10">
              {t("viewer_open_full", "Open full page")}
            </a>
          {/if}
          <button type="button" onclick={() => viewerEl?.close()} class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800">
            {t("viewer_close", "Close")}
          </button>
        </div>
      </header>

      {#if viewer.state === "blocked"}
        <div class="space-y-3 px-4 py-4 text-sm">
          <p>{t("popup_blocked", "Your browser blocked the new tab. Open the dashboard here:")}</p>
          <a href={viewer.url} target="_blank" rel="noopener" class="inline-flex rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700">
            {t("popup_open", "Open dashboard")}
          </a>
        </div>
      {:else}
        <div class="relative flex-1">
          {#if viewer.state === "loading"}
            <p class="absolute inset-x-0 top-4 text-center text-sm text-gray-500">{t("viewer_loading", "Loading dashboard…")}</p>
          {:else if viewer.state === "timeout" || viewer.state === "error"}
            <div role="alert" class="absolute inset-x-4 top-4 z-10 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
              {viewer.state === "timeout"
                ? t("viewer_timeout", "The dashboard did not respond within 30 seconds.")
                : t("viewer_error", "The dashboard could not be loaded.")}
            </div>
          {/if}
          <iframe
            title={viewer.name}
            src={viewer.url}
            onload={onFrameLoad}
            onerror={onFrameError}
            class="h-full w-full border-0"
          ></iframe>
        </div>
      {/if}
    </div>
  {/if}
</dialog>
