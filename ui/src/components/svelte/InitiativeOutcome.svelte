<script lang="ts">
  /**
   * InitiativeOutcome — User Acknowledgment of Initiative Notification
   * (HU-IN17, specs/005-explore-initiatives US8). The proposer reads whether
   * their initiative was accepted or rejected, with the reviewer's message.
   * Opening records NOTHING — reading is not acknowledging; only the explicit
   * "Got it" marks the notice handled.
   */
  import { onMount } from "svelte";
  import { acknowledgeCollaboration, getCollaboration } from "@/lib/collaborations";
  import { notifyChanged } from "@/lib/notificationsStore";
  import { formatRelative } from "@/lib/datatable";
  import { apiErrorDetail } from "@/lib/api";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";
  import type { CollaborationDetail } from "@/types/api";

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
  const locale = (): string =>
    (typeof localStorage !== "undefined" && localStorage.getItem("lang")) || "en";

  let collab = $state<CollaborationDetail | null>(null);
  let loading = $state(true);
  let notFound = $state(false);
  let busy = $state(false);

  const accepted = $derived(collab?.type === "ACCEPTANCE");
  const pending = $derived(collab?.current_status === "PENDING");

  onMount(() => {
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);
    void load();
    return () => window.removeEventListener("languageChanged", onLang);
  });

  async function load(): Promise<void> {
    const id = Number(new URLSearchParams(location.search).get("collab"));
    try {
      if (!id) throw new Error("missing");
      const c = await getCollaboration(id);
      if (c.type !== "ACCEPTANCE" && c.type !== "REJECTION") throw new Error("wrong type");
      collab = c;
    } catch {
      notFound = true;
    } finally {
      loading = false;
    }
  }

  async function acknowledge(): Promise<void> {
    if (!collab || busy) return;
    busy = true;
    try {
      await acknowledgeCollaboration(collab.id);
      notifyChanged();
      window.location.href = "/inits/my_initiative_requests";
    } catch (err) {
      showToast(apiErrorDetail(err, t("inits_show_collab.error", "Could not acknowledge this notice")), "error");
      busy = false;
    }
  }
</script>

<article class="overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
  {#if loading}
    <p class="px-6 py-5 text-sm text-gray-400">{t("common.loading", "Loading…")}</p>
  {:else if notFound || !collab}
    <div class="space-y-2 px-6 py-5">
      <p class="text-sm text-red-600 dark:text-red-400">{t("inits_show_collab.not_found", "This notice could not be found.")}</p>
      <a href="/inits/my_initiative_requests" class="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400">{t("inits_diagnose.to_requests", "Go to My Initiative Requests")} →</a>
    </div>
  {:else}
    <div class={`flex items-start gap-4 bg-gradient-to-br px-6 py-5 text-white ${accepted ? "from-emerald-500 to-emerald-600" : "from-red-500 to-red-600"}`}>
      <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/20" aria-hidden="true">
        {#if accepted}
          <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m5 12.5 4.5 4.5L19 7.5" stroke-linecap="round" stroke-linejoin="round" /></svg>
        {:else}
          <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6 6 18" stroke-linecap="round" /></svg>
        {/if}
      </span>
      <div class="min-w-0">
        <h1 class="text-lg font-bold">
          {accepted ? t("inits_show_collab.title_accepted", "Your initiative was accepted") : t("inits_show_collab.title_rejected", "Your initiative was rejected")}
        </h1>
        <p class="mt-0.5 truncate text-sm text-white/85">{collab.initiative?.name ?? `#${collab.init}`} · {formatRelative(collab.created_at, locale())}</p>
      </div>
    </div>

    <div class="space-y-4 px-6 py-5">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-gray-400">{t("inits_show_collab.message", "Reviewer's message")}</p>
        <p class="mt-1 whitespace-pre-line text-sm text-gray-800 dark:text-gray-200">{collab.content || t("inits_show_collab.no_message", "The reviewer left no message.")}</p>
      </div>
      {#if !pending}
        <p class="text-sm text-gray-500 dark:text-gray-400">{t("inits_show_collab.handled", "You already acknowledged this outcome.")}</p>
      {/if}
    </div>

    <div class="flex flex-col gap-3 border-t border-gray-200 px-6 py-4 sm:flex-row sm:justify-end dark:border-gray-800">
      <button type="button" onclick={() => history.back()} class="inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800">{t("inits_show_collab.back", "Back")}</button>
      {#if pending}
        <button type="button" disabled={busy} onclick={acknowledge} class={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-60 ${accepted ? "bg-emerald-600 hover:bg-emerald-700" : "bg-red-600 hover:bg-red-700"}`}>{t("inits_show_collab.acknowledge", "Got it")}</button>
      {/if}
    </div>
  {/if}
</article>
