/**
 * Actions API service — the frontend side of the generic `actions` event log.
 *
 * Phase 1 covers voting (HU-LI05): votes are `actions` rows of type VOTE with
 * content POSITIVE/NEGATIVE. The backend keeps a single vote per (user, asset)
 * and toggles it off when the same value is re-sent, so the UI can simply POST
 * the clicked value and repaint from the authoritative `VoteTally` it returns.
 *
 * `summarizeVotes` groups one bounded bulk fetch into per-asset summaries so a
 * gallery can pre-fill every card's score without an N+1 of per-asset calls
 * (mirrors how catalogs bulk-fetch characterizations). A dedicated bulk
 * vote-tally endpoint is a future optimization if catalogs grow large.
 */
import { apiGet, apiPost, apiDelete, buildQueryString } from "./api";
import type { Action, VoteTally, WorkflowStage } from "../types/api";

export const VOTE_POSITIVE = "POSITIVE";
export const VOTE_NEGATIVE = "NEGATIVE";
export type VoteValue = "POSITIVE" | "NEGATIVE";

/** Bounded list of actions (all types) — used for client-side vote grouping. */
export async function getActions(skip = 0, limit = 1000): Promise<Action[]> {
  return apiGet<Action[]>(`/api/actions/${buildQueryString({ skip, limit })}`);
}

/** Authoritative vote tally for one asset (+ the current user's `my_vote`). */
export async function getVoteTally(assetId: number): Promise<VoteTally> {
  return apiGet<VoteTally>(
    `/api/actions/votes/asset/${encodeURIComponent(String(assetId))}`,
  );
}

/** The asset's current review stage (latest workflow action), or null. */
export async function getWorkflowStage(
  assetId: number,
): Promise<WorkflowStage | null> {
  return apiGet<WorkflowStage | null>(
    `/api/actions/workflow/asset/${encodeURIComponent(String(assetId))}`,
  );
}

/**
 * Set or flip a user's vote. Re-sending the current value clears it (the
 * backend toggles), so callers can pass the clicked value directly. Returns the
 * refreshed tally to repaint with.
 */
export async function setVote(
  userId: number,
  assetId: number,
  content: VoteValue,
): Promise<VoteTally> {
  return apiPost<VoteTally, { user_id: number; asset: number; content: string }>(
    "/api/actions/votes",
    { user_id: userId, asset: assetId, content },
  );
}

/** Clear a user's vote on an asset (logical delete of the VOTE action). */
export async function clearVote(
  userId: number,
  assetId: number,
): Promise<VoteTally> {
  return apiDelete<VoteTally>(
    `/api/actions/votes/${encodeURIComponent(String(userId))}/${encodeURIComponent(String(assetId))}`,
  );
}

export interface VoteSummary {
  score: number;
  positive: number;
  negative: number;
  myVote: string | null;
}

/**
 * Group a bulk action list into per-asset vote summaries. Pass `userId` to also
 * resolve each asset's `myVote`. Only active VOTE rows are counted.
 */
export function summarizeVotes(
  actions: Action[],
  userId?: number,
): Map<number, VoteSummary> {
  const map = new Map<number, VoteSummary>();
  for (const a of actions) {
    if (a.type !== "VOTE" || a.is_active === false) continue;
    const assetId = Number(a.asset);
    const s =
      map.get(assetId) ?? { score: 0, positive: 0, negative: 0, myVote: null };
    if (a.content === VOTE_POSITIVE) {
      s.positive += 1;
      s.score += 1;
    } else if (a.content === VOTE_NEGATIVE) {
      s.negative += 1;
      s.score -= 1;
    }
    if (userId !== undefined && Number(a.user_id) === userId) {
      s.myVote = a.content ?? null;
    }
    map.set(assetId, s);
  }
  return map;
}
