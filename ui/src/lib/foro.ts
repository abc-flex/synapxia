/**
 * foro — the asset "discussion" feature (HU-LI06): comments, questions and
 * threaded answers, all layered over the generic `actions` event log.
 *
 * Backend storage: `actions` rows of type COMMENT / QUESTION / ANSWER (an
 * ANSWER threads to its QUESTION via `parent`). No new table — this mirrors how
 * voting reuses the same substrate. This module is the data layer: a thin
 * wrapper over the `/api/actions/*` foro routes plus the pure grouping/count
 * helpers. The discussion UI (feed/composers/answers) now lives in the Svelte
 * island `components/svelte/Foro.svelte` (mounted from Foro.astro), which reuses
 * these services and renders user content via Svelte's escaping (never
 * innerHTML) — the XSS guard the spec calls out.
 */
import { apiGet, apiPost, apiDelete } from "./api";
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
