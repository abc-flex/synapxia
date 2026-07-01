<script lang="ts">
  /**
   * Foro — the asset discussion (HU-LI06) as a Svelte island. Third migration
   * after ShowAction + NotificationBell, and the first that replaces a heavy
   * hand-rolled DOM controller (the old `mountForo` in lib/foro.ts, ~320 lines of
   * createElement/innerHTML) with a declarative component.
   *
   * Comments, questions and threaded answers are stored as `actions` rows (type
   * COMMENT / QUESTION / ANSWER, an ANSWER threading to its QUESTION via
   * `parent`) — no new table. This island reuses the EXISTING services unchanged
   * (getDiscussion / addComment / addQuestion / addAnswer / deleteParticipation /
   * groupDiscussion) plus `translate()` i18n; only the render + state layer is
   * Svelte. Mounted manually from Foro.astro (see astro.config.mjs — not the
   * @astrojs/svelte island mechanism).
   *
   * All user content renders through Svelte's default text interpolation (never
   * {@html}), so a comment can't inject markup — the XSS guard the spec calls out.
   */
  import { onMount } from "svelte";
  import {
    getDiscussion,
    addComment,
    addQuestion,
    addAnswer,
    deleteParticipation,
    groupDiscussion,
  } from "@/lib/foro";
  import { getUser } from "@/lib/auth";
  import { formatRelative } from "@/lib/datatable";
  import { translate } from "@/utils/i18nClient";
  import { showToast } from "@/lib/toast";
  import type { DiscussionItem } from "@/types/api";

  let { modalId }: { modalId: string } = $props();

  let items = $state<DiscussionItem[]>([]);
  let statusText = $state("");
  let postType = $state<"COMMENT" | "QUESTION">("COMMENT");
  let draft = $state("");
  // Per-question inline answer composer state (keyed by question id).
  let answerOpen = $state<Record<number, boolean>>({});
  let answerDraft = $state<Record<number, string>>({});
  let langTick = $state(0); // bump on language switch → re-localize labels

  let assetId: number | null = null;
  let loadSeq = 0;
  let rootEl = $state<HTMLElement | undefined>(undefined);
  let composerEl = $state<HTMLTextAreaElement | undefined>(undefined);

  const currentUser = (): { id: number } | null => {
    const u = getUser() as { id?: number } | null;
    if (!u || (!u.id && u.id !== 0)) return null;
    return { id: Number(u.id) };
  };
  let me = $state<{ id: number } | null>(null);

  const t = (key: string, fallback: string): string => {
    void langTick; // reactive dep
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

  // One merged, chronological feed: comments + questions as top-level entries,
  // newest first; answers stay threaded inside their question card.
  const entries = $derived.by(() => {
    const { comments, questions } = groupDiscussion(items);
    const list = [
      ...comments.map((c) => ({
        kind: "comment" as const,
        item: c,
        answers: [] as DiscussionItem[],
      })),
      ...questions.map((th) => ({
        kind: "question" as const,
        item: th.question,
        answers: th.answers,
      })),
    ];
    list.sort((a, b) => {
      if (a.item.created_at !== b.item.created_at)
        return a.item.created_at < b.item.created_at ? 1 : -1; // newest first
      return b.item.id - a.item.id; // deterministic tiebreak for equal timestamps
    });
    return list;
  });

  const composerPlaceholder = $derived(
    postType === "QUESTION"
      ? t("foro.question_placeholder", "Ask a question…")
      : t("foro.comment_placeholder", "Write a comment…"),
  );

  const canDelete = (item: DiscussionItem): boolean =>
    !!me && me.id === Number(item.user_id);

  const tagClass = (isQuestion: boolean): string =>
    "inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide " +
    (isQuestion
      ? "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300"
      : "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300");

  const typeToggleClass = (active: boolean): string =>
    "rounded px-3 py-1 text-xs font-semibold transition-colors " +
    (active ? "bg-indigo-600 text-white" : "text-gray-600 dark:text-gray-300");

  async function load(id: number): Promise<void> {
    const seq = ++loadSeq;
    assetId = id;
    items = [];
    answerOpen = {};
    answerDraft = {};
    statusText = t("foro.loading", "Loading discussion…");
    try {
      const data = await getDiscussion(id);
      if (seq !== loadSeq) return; // superseded by a newer open()
      items = data;
      statusText = "";
    } catch {
      if (seq !== loadSeq) return;
      statusText = t("foro.error", "Could not load the discussion.");
    }
  }

  async function reload(): Promise<void> {
    if (assetId != null) await load(assetId);
  }

  function guardedUser(): { id: number } | null {
    const u = currentUser();
    if (!u) {
      showToast(t("foro.sign_in", "Sign in to participate"), "error");
      return null;
    }
    return u;
  }

  async function submitPost(): Promise<void> {
    const u = guardedUser();
    const text = draft.trim();
    if (!u || assetId == null || !text) return;
    try {
      if (postType === "QUESTION") await addQuestion(u.id, assetId, text);
      else await addComment(u.id, assetId, text);
      draft = "";
      await reload();
    } catch (err) {
      showToast(err instanceof Error ? err.message : t("foro.error", "Something went wrong"), "error");
    }
  }

  function openAnswer(qid: number): void {
    answerOpen = { ...answerOpen, [qid]: true };
  }

  async function submitAnswer(qid: number): Promise<void> {
    const u = guardedUser();
    const text = (answerDraft[qid] || "").trim();
    if (!u || assetId == null || !text) return;
    try {
      await addAnswer(u.id, assetId, text, qid);
      answerDraft = { ...answerDraft, [qid]: "" };
      answerOpen = { ...answerOpen, [qid]: false };
      await reload();
    } catch (err) {
      showToast(err instanceof Error ? err.message : t("foro.error", "Something went wrong"), "error");
    }
  }

  async function remove(id: number): Promise<void> {
    try {
      await deleteParticipation(id);
      await reload();
    } catch (err) {
      showToast(err instanceof Error ? err.message : t("foro.error", "Something went wrong"), "error");
    }
  }

  // Keep the originating card's discuss badge in sync with the live count.
  $effect(() => {
    const n = items.length;
    if (assetId == null) return;
    const badge = document.querySelector<HTMLElement>(
      `[data-card][data-id="${assetId}"] [data-discuss-count]`,
    );
    if (!badge) return;
    badge.textContent = n > 0 ? String(n) : "";
    badge.classList.toggle("hidden", n === 0);
  });

  onMount(() => {
    me = currentUser();
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);

    // Load on the same open trigger the detail controller listens for. When the
    // opener carries `data-foro-focus` (the card's discuss button), scroll the
    // discussion into view and focus the composer once the modal is open.
    const onDocClick = (e: MouseEvent) => {
      const opener = (e.target as HTMLElement).closest?.(`[data-modal-open="${modalId}"]`);
      if (!opener) return;
      const id = (opener as HTMLElement).dataset.assetId;
      if (id) void load(Number(id));
      if ((opener as HTMLElement).dataset.foroFocus) {
        setTimeout(() => {
          rootEl?.scrollIntoView({ behavior: "smooth", block: "start" });
          composerEl?.focus();
        }, 200);
      }
    };
    document.addEventListener("click", onDocClick);

    return () => {
      window.removeEventListener("languageChanged", onLang);
      document.removeEventListener("click", onDocClick);
    };
  });
</script>

<!-- Lives alone in the modal's "Discussion" tab (which labels it), so no
     in-section heading. Minimalist layout: the feed reads first, with a slim
     composer pinned at the bottom. -->
<section bind:this={rootEl}>
  {#if statusText}
    <p class="text-sm text-gray-400 dark:text-gray-500">{statusText}</p>
  {/if}

  <!-- One merged, chronological feed: comments + questions (with threaded answers). -->
  <div class="space-y-4">
    {#each entries as entry (entry.item.id)}
      <div class="group border-b border-gray-100 pb-4 last:border-0 dark:border-gray-800">
        <div class="mb-1 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <span class={tagClass(entry.kind === "question")}>
            {entry.kind === "question"
              ? t("foro.tag_question", "Question")
              : t("foro.tag_comment", "Comment")}
          </span>
          <span class="font-semibold text-gray-700 dark:text-gray-300">
            {entry.item.author || t("foro.anonymous", "Someone")}
          </span>
          <span>{formatRelative(entry.item.created_at, locale())}</span>
          {#if canDelete(entry.item)}
            <button
              type="button"
              class="ml-auto text-xs font-medium text-gray-400 opacity-0 transition-opacity hover:text-red-600 focus:opacity-100 group-hover:opacity-100 group-focus-within:opacity-100 dark:hover:text-red-400"
              onclick={() => remove(entry.item.id)}
            >{t("foro.delete", "Delete")}</button>
          {/if}
        </div>
        <p class="whitespace-pre-wrap break-words text-sm text-gray-800 dark:text-gray-200">
          {entry.item.content || ""}
        </p>

        {#if entry.kind === "question"}
          {#each entry.answers as answer (answer.id)}
            <div class="group ml-5 mt-2 border-l-2 border-gray-200 pl-3 dark:border-gray-700">
              <div class="mb-1 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <span class="font-semibold text-gray-700 dark:text-gray-300">
                  {answer.author || t("foro.anonymous", "Someone")}
                </span>
                <span>{formatRelative(answer.created_at, locale())}</span>
                {#if canDelete(answer)}
                  <button
                    type="button"
                    class="ml-auto text-xs font-medium text-gray-400 opacity-0 transition-opacity hover:text-red-600 focus:opacity-100 group-hover:opacity-100 group-focus-within:opacity-100 dark:hover:text-red-400"
                    onclick={() => remove(answer.id)}
                  >{t("foro.delete", "Delete")}</button>
                {/if}
              </div>
              <p class="whitespace-pre-wrap break-words text-sm text-gray-500 dark:text-gray-400">
                {answer.content || ""}
              </p>
            </div>
          {/each}

          <!-- Answer affordance (only when signed in): a subtle link that reveals
               an inline composer on click — keeps the thread minimal until you act. -->
          {#if me}
            {#if answerOpen[entry.item.id]}
              <div class="ml-5 mt-2 flex items-start gap-2">
                <textarea
                  rows="1"
                  bind:value={answerDraft[entry.item.id]}
                  placeholder={t("foro.answer_placeholder", "Write an answer…")}
                  class="min-h-[2.25rem] flex-1 resize-y rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                ></textarea>
                <button
                  type="button"
                  class="shrink-0 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-indigo-700"
                  onclick={() => submitAnswer(entry.item.id)}
                >{t("foro.answer", "Answer")}</button>
              </div>
            {:else}
              <button
                type="button"
                class="ml-5 mt-2 text-xs font-medium text-indigo-600 opacity-0 transition-opacity hover:underline focus:opacity-100 group-hover:opacity-100 group-focus-within:opacity-100 dark:text-indigo-400"
                onclick={() => openAnswer(entry.item.id)}
              >{t("foro.answer", "Answer")}</button>
            {/if}
          {/if}
        {/if}
      </div>
    {/each}

    {#if !statusText && entries.length === 0}
      <p class="text-sm text-gray-400 dark:text-gray-500">{t("foro.empty", "No discussion yet.")}</p>
    {/if}
  </div>

  <!-- Slim composer at the end of the discussion: pick Comment or Question, then post. -->
  <div class="mt-5 border-t border-gray-200 pt-4 dark:border-gray-800">
    <div class="mb-2 inline-flex rounded-md border border-gray-300 p-0.5 dark:border-gray-700" role="group">
      <button
        type="button"
        aria-pressed={postType === "COMMENT"}
        class={typeToggleClass(postType === "COMMENT")}
        onclick={() => (postType = "COMMENT")}
      >{t("foro.tag_comment", "Comment")}</button>
      <button
        type="button"
        aria-pressed={postType === "QUESTION"}
        class={typeToggleClass(postType === "QUESTION")}
        onclick={() => (postType = "QUESTION")}
      >{t("foro.tag_question", "Question")}</button>
    </div>
    <div class="flex items-end gap-2">
      <textarea
        bind:this={composerEl}
        bind:value={draft}
        rows="1"
        placeholder={composerPlaceholder}
        class="min-h-[2.5rem] flex-1 resize-y rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
      ></textarea>
      <button
        type="button"
        class="shrink-0 rounded-md bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
        onclick={submitPost}
      >{t("foro.post", "Post")}</button>
    </div>
  </div>
</section>
