/**
 * foro — the asset "discussion" feature (HU-LI06): comments, questions and
 * threaded answers, all layered over the generic `actions` event log.
 *
 * Backend storage: `actions` rows of type COMMENT / QUESTION / ANSWER (an
 * ANSWER threads to its QUESTION via `parent`). No new table — this mirrors how
 * voting reuses the same substrate. The service is a thin wrapper over the
 * `/api/actions/*` foro routes; `mountForo` hydrates the discussion section
 * inside the shared CatalogDetailModal and wires the composers.
 *
 * User-supplied content is always rendered with `textContent` (never innerHTML)
 * so a comment can't inject markup — the XSS guard the spec calls out.
 */
import { apiGet, apiPost, apiDelete } from "./api";
import { getUser } from "./auth";
import { formatRelative } from "./datatable";
import { translate } from "@/utils/i18nClient";
import type { Action, DiscussionItem } from "../types/api";

// ── Service ──────────────────────────────────────────────────────────────────

/** The full discussion for an asset (comments + questions + answers), oldest first. */
export async function getDiscussion(assetId: number): Promise<DiscussionItem[]> {
  return apiGet<DiscussionItem[]>(
    `/api/actions/discussion/asset/${encodeURIComponent(String(assetId))}`,
  );
}

export async function addComment(
  userId: number, assetId: number, content: string,
): Promise<DiscussionItem> {
  return apiPost<DiscussionItem, { user_id: number; asset: number; content: string }>(
    "/api/actions/comments",
    { user_id: userId, asset: assetId, content },
  );
}

export async function addQuestion(
  userId: number, assetId: number, content: string,
): Promise<DiscussionItem> {
  return apiPost<DiscussionItem, { user_id: number; asset: number; content: string }>(
    "/api/actions/questions",
    { user_id: userId, asset: assetId, content },
  );
}

export async function addAnswer(
  userId: number, assetId: number, content: string, parent: number,
): Promise<DiscussionItem> {
  return apiPost<
    DiscussionItem,
    { user_id: number; asset: number; content: string; parent: number }
  >("/api/actions/answers", { user_id: userId, asset: assetId, content, parent });
}

/** Logical-delete a participation (reuses the generic action delete route). */
export async function deleteParticipation(id: number): Promise<unknown> {
  return apiDelete<unknown>(`/api/actions/${encodeURIComponent(String(id))}`);
}

export interface QuestionThread {
  question: DiscussionItem;
  answers: DiscussionItem[];
}

/** Split a flat discussion list into top-level comments and question threads. */
export function groupDiscussion(items: DiscussionItem[]): {
  comments: DiscussionItem[];
  questions: QuestionThread[];
} {
  const comments: DiscussionItem[] = [];
  const threads = new Map<number, QuestionThread>();
  const pendingAnswers: DiscussionItem[] = [];

  for (const it of items) {
    if (it.type === "COMMENT") comments.push(it);
    else if (it.type === "QUESTION") threads.set(it.id, { question: it, answers: [] });
    else if (it.type === "ANSWER") pendingAnswers.push(it);
  }
  for (const ans of pendingAnswers) {
    const thread = ans.parent != null ? threads.get(ans.parent) : undefined;
    if (thread) thread.answers.push(ans);
  }
  return { comments, questions: [...threads.values()] };
}

/**
 * Per-asset count of active discussion messages (comments + questions + answers)
 * from one bulk `getActions` list — used to pre-fill the card's discuss badge
 * without an N+1 of per-asset calls (mirrors `summarizeVotes`).
 */
export function summarizeDiscussionCounts(actions: Action[]): Map<number, number> {
  const map = new Map<number, number>();
  for (const a of actions) {
    if (a.is_active === false) continue;
    if (a.type !== "COMMENT" && a.type !== "QUESTION" && a.type !== "ANSWER") continue;
    const id = Number(a.asset);
    map.set(id, (map.get(id) ?? 0) + 1);
  }
  return map;
}

// ── Controller (hydrates the discussion section in CatalogDetailModal) ────────

interface ForoConfig {
  /** The detail dialog id, e.g. "mcp-view-modal". The foro shell lives at
   * `#${modalId}-foro` (rendered by Foro.astro). */
  modalId: string;
}

const tr = (key: string, fallback: string): string => {
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

/**
 * Mount the discussion section for one detail modal. Self-contained: it listens
 * for the same open trigger the detail controller uses (`[data-modal-open=…]`),
 * loads the discussion for the opened asset, and wires the comment / question /
 * answer composers. Call once per detail modal (mountCatalogDetail does this).
 */
export function mountForo(cfg: ForoConfig): void {
  if (typeof window === "undefined") return;
  const { modalId } = cfg;

  const root = document.getElementById(`${modalId}-foro`);
  if (!root) return;

  const commentsEl = root.querySelector<HTMLElement>("[data-foro-comments]");
  const questionsEl = root.querySelector<HTMLElement>("[data-foro-questions]");
  const statusEl = root.querySelector<HTMLElement>("[data-foro-status]");
  const commentInput = root.querySelector<HTMLTextAreaElement>("[data-foro-comment-input]");
  const commentSubmit = root.querySelector<HTMLButtonElement>("[data-foro-comment-submit]");
  const questionInput = root.querySelector<HTMLTextAreaElement>("[data-foro-question-input]");
  const questionSubmit = root.querySelector<HTMLButtonElement>("[data-foro-question-submit]");

  let assetId: number | null = null;

  const currentUser = (): { id: number } | null => {
    const u = getUser() as any;
    if (!u || (!u.id && u.id !== 0)) return null;
    return { id: Number(u.id) };
  };

  const setStatus = (text: string) => {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.classList.toggle("hidden", !text);
  };

  // ── Renderers (all user content via textContent — XSS-safe) ────────────────
  function metaLine(item: DiscussionItem): HTMLElement {
    const meta = document.createElement("div");
    meta.className = "mb-1 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400";
    const who = document.createElement("span");
    who.className = "font-semibold text-gray-700 dark:text-gray-300";
    who.textContent = item.author || tr("foro.anonymous", "Someone");
    const when = document.createElement("span");
    when.textContent = formatRelative(item.created_at, locale());
    meta.append(who, when);
    return meta;
  }

  function bodyText(item: DiscussionItem): HTMLElement {
    const p = document.createElement("p");
    p.className = "whitespace-pre-wrap break-words text-sm text-gray-800 dark:text-gray-200";
    p.textContent = item.content || "";
    return p;
  }

  function deleteControl(item: DiscussionItem): HTMLButtonElement | null {
    const me = currentUser();
    if (!me || me.id !== Number(item.user_id)) return null;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.foroDelete = String(item.id);
    btn.className =
      "ml-auto text-xs font-medium text-gray-400 hover:text-red-600 dark:hover:text-red-400";
    btn.textContent = tr("foro.delete", "Delete");
    return btn;
  }

  function commentNode(item: DiscussionItem): HTMLElement {
    const card = document.createElement("div");
    card.className = "rounded-lg border border-gray-200 p-3 dark:border-gray-800";
    const head = metaLine(item);
    const del = deleteControl(item);
    if (del) head.appendChild(del);
    card.append(head, bodyText(item));
    return card;
  }

  function answerNode(item: DiscussionItem): HTMLElement {
    const card = document.createElement("div");
    card.className =
      "ml-4 mt-2 rounded-lg border-l-2 border-indigo-200 bg-gray-50 p-2.5 dark:border-indigo-900/50 dark:bg-gray-800/40";
    const head = metaLine(item);
    const del = deleteControl(item);
    if (del) head.appendChild(del);
    card.append(head, bodyText(item));
    return card;
  }

  function questionNode(thread: QuestionThread): HTMLElement {
    const { question, answers } = thread;
    const card = document.createElement("div");
    card.className = "rounded-lg border border-gray-200 p-3 dark:border-gray-800";
    const head = metaLine(question);
    const del = deleteControl(question);
    if (del) head.appendChild(del);
    card.append(head, bodyText(question));

    for (const a of answers) card.appendChild(answerNode(a));

    // Inline answer composer (only when signed in).
    if (currentUser()) {
      const wrap = document.createElement("div");
      wrap.className = "ml-4 mt-2 flex items-start gap-2";
      const ta = document.createElement("textarea");
      ta.rows = 1;
      ta.dataset.foroAnswerInput = String(question.id);
      ta.placeholder = tr("foro.answer_placeholder", "Write an answer…");
      ta.className =
        "min-h-[2.25rem] flex-1 resize-y rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-sm text-gray-900 focus:border-indigo-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100";
      const btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.foroAnswerSubmit = String(question.id);
      btn.className =
        "shrink-0 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-indigo-700";
      btn.textContent = tr("foro.answer", "Answer");
      wrap.append(ta, btn);
      card.appendChild(wrap);
    }
    return card;
  }

  function renderEmpty(target: HTMLElement | null, msgKey: string, fallback: string) {
    if (!target) return;
    const p = document.createElement("p");
    p.className = "text-sm text-gray-400 dark:text-gray-500";
    p.textContent = tr(msgKey, fallback);
    target.appendChild(p);
  }

  function render(items: DiscussionItem[]) {
    if (!commentsEl || !questionsEl) return;
    commentsEl.innerHTML = "";
    questionsEl.innerHTML = "";
    const { comments, questions } = groupDiscussion(items);

    if (comments.length === 0) renderEmpty(commentsEl, "foro.empty_comments", "No comments yet.");
    else for (const c of comments) commentsEl.appendChild(commentNode(c));

    if (questions.length === 0) renderEmpty(questionsEl, "foro.empty_questions", "No questions yet.");
    else for (const q of questions) questionsEl.appendChild(questionNode(q));

    // Keep the originating card's discuss badge in sync with the live count.
    if (assetId != null) {
      const badge = document.querySelector<HTMLElement>(
        `[data-card][data-id="${assetId}"] [data-discuss-count]`);
      if (badge) {
        const n = items.length;
        badge.textContent = n > 0 ? String(n) : "";
        badge.classList.toggle("hidden", n === 0);
      }
    }
  }

  async function load(id: number) {
    assetId = id;
    if (commentsEl) commentsEl.innerHTML = "";
    if (questionsEl) questionsEl.innerHTML = "";
    setStatus(tr("foro.loading", "Loading discussion…"));
    try {
      const items = await getDiscussion(id);
      setStatus("");
      render(items);
    } catch {
      setStatus(tr("foro.error", "Could not load the discussion."));
    }
  }

  async function reload() {
    if (assetId != null) await load(assetId);
  }

  // ── Composer actions ───────────────────────────────────────────────────────
  function guardedUser(): { id: number } | null {
    const me = currentUser();
    if (!me) {
      (window as any).showToast?.(tr("foro.sign_in", "Sign in to participate"), "error");
      return null;
    }
    return me;
  }

  async function submitComment() {
    const me = guardedUser();
    const text = (commentInput?.value || "").trim();
    if (!me || assetId == null || !text) return;
    try {
      await addComment(me.id, assetId, text);
      if (commentInput) commentInput.value = "";
      await reload();
    } catch (err) {
      (window as any).showToast?.(
        err instanceof Error ? err.message : tr("foro.error", "Something went wrong"), "error");
    }
  }

  async function submitQuestion() {
    const me = guardedUser();
    const text = (questionInput?.value || "").trim();
    if (!me || assetId == null || !text) return;
    try {
      await addQuestion(me.id, assetId, text);
      if (questionInput) questionInput.value = "";
      await reload();
    } catch (err) {
      (window as any).showToast?.(
        err instanceof Error ? err.message : tr("foro.error", "Something went wrong"), "error");
    }
  }

  async function submitAnswer(parentId: number, input: HTMLTextAreaElement) {
    const me = guardedUser();
    const text = (input.value || "").trim();
    if (!me || assetId == null || !text) return;
    try {
      await addAnswer(me.id, assetId, text, parentId);
      await reload();
    } catch (err) {
      (window as any).showToast?.(
        err instanceof Error ? err.message : tr("foro.error", "Something went wrong"), "error");
    }
  }

  async function remove(id: number) {
    try {
      await deleteParticipation(id);
      await reload();
    } catch (err) {
      (window as any).showToast?.(
        err instanceof Error ? err.message : tr("foro.error", "Something went wrong"), "error");
    }
  }

  // ── Wiring ─────────────────────────────────────────────────────────────────
  commentSubmit?.addEventListener("click", submitComment);
  questionSubmit?.addEventListener("click", submitQuestion);

  // Delegated handlers for the dynamic answer composers + delete buttons.
  root.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    const ansBtn = target.closest<HTMLElement>("[data-foro-answer-submit]");
    if (ansBtn) {
      const qid = Number(ansBtn.dataset.foroAnswerSubmit);
      const input = root.querySelector<HTMLTextAreaElement>(
        `[data-foro-answer-input="${qid}"]`);
      if (input) submitAnswer(qid, input);
      return;
    }
    const delBtn = target.closest<HTMLElement>("[data-foro-delete]");
    if (delBtn) {
      remove(Number(delBtn.dataset.foroDelete));
    }
  });

  // Load on the same open trigger the detail controller listens for. When the
  // opener carries `data-foro-focus` (the card's discuss button), scroll the
  // discussion into view and focus the comment composer once the modal is open.
  document.addEventListener("click", (e) => {
    const opener = (e.target as HTMLElement).closest?.(`[data-modal-open="${modalId}"]`);
    if (!opener) return;
    const id = (opener as HTMLElement).dataset.assetId;
    if (id) load(Number(id));
    if ((opener as HTMLElement).dataset.foroFocus) {
      setTimeout(() => {
        root.scrollIntoView({ behavior: "smooth", block: "start" });
        commentInput?.focus();
      }, 200);
    }
  });
}
