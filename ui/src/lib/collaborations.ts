/**
 * Initiative collaborations for Initiative Management: the History timeline
 * (read-only) and the Discussion thread (read + write). Same shapes as the
 * asset readers, so the shared `mountHistory` controller and the `Foro` island
 * render them unchanged (`initiativeForoApi` is Foro's `api` prop).
 */
import { apiDelete, apiGet, apiPost, apiPut, buildQueryString } from "./api";
import type {
  Collaboration,
  CollaborationDetail,
  DiscussionItem,
  HistoryEntry,
  InitDiscussionItem,
  InitiativeRequest,
  InitNotificationFeed,
  InitVoteTally,
} from "@/types/api";

const enc = (v: number) => encodeURIComponent(String(v));

export async function getInitiativeHistory(initId: number, skip = 0, limit = 200): Promise<HistoryEntry[]> {
  return apiGet<HistoryEntry[]>(
    `/api/collaborations/history/init/${enc(initId)}${buildQueryString({ skip, limit })}`,
  );
}

/** The thread in the `DiscussionItem` shape Foro expects (`init` → `asset`
 *  slot, which Foro only uses as an opaque key). */
const toDiscussionItem = ({ init, ...rest }: InitDiscussionItem): DiscussionItem => ({ ...rest, asset: init });

export async function getInitiativeDiscussion(initId: number): Promise<DiscussionItem[]> {
  const rows = await apiGet<InitDiscussionItem[]>(`/api/collaborations/discussion/init/${enc(initId)}`);
  return rows.map(toDiscussionItem);
}

// ── Discussion writes. The author is always the signed-in user (the API takes
// it from the session); `_userId` only keeps the signature Foro expects.

export async function addInitiativeComment(_userId: number, initId: number, content: string): Promise<DiscussionItem> {
  return toDiscussionItem(await apiPost<InitDiscussionItem, { init: number; content: string }>(
    "/api/collaborations/comments", { init: initId, content }));
}

export async function addInitiativeQuestion(_userId: number, initId: number, content: string): Promise<DiscussionItem> {
  return toDiscussionItem(await apiPost<InitDiscussionItem, { init: number; content: string }>(
    "/api/collaborations/questions", { init: initId, content }));
}

export async function addInitiativeAnswer(
  _userId: number, initId: number, content: string, parent: number,
): Promise<DiscussionItem> {
  return toDiscussionItem(await apiPost<InitDiscussionItem, { init: number; content: string; parent: number }>(
    "/api/collaborations/answers", { init: initId, content, parent }));
}

/** Delete one of your own comments / questions / answers. */
export async function deleteInitiativeParticipation(id: number): Promise<unknown> {
  return apiDelete<unknown>(`/api/collaborations/${enc(id)}`);
}

/** The full Foro `api` for an initiative thread. */
export const initiativeForoApi = {
  getDiscussion: getInitiativeDiscussion,
  addComment: addInitiativeComment,
  addQuestion: addInitiativeQuestion,
  addAnswer: addInitiativeAnswer,
  deleteParticipation: deleteInitiativeParticipation,
};

// ── Contribution workflow (specs/005-explore-initiatives) ────────────────────

/** One of the caller's own collaborations, with the initiative embedded. */
export async function getCollaboration(id: number): Promise<CollaborationDetail> {
  return apiGet<CollaborationDetail>(`/api/collaborations/${enc(id)}`);
}

// Votes — one active vote per user and initiative; the voter is the session user.

export async function getInitiativeVoteTally(initId: number): Promise<InitVoteTally> {
  return apiGet<InitVoteTally>(`/api/collaborations/votes/init/${enc(initId)}`);
}

/** Set the vote. Sending the vote already held withdraws it (toggle). */
export async function setInitiativeVote(initId: number, content: "POSITIVE" | "NEGATIVE"): Promise<InitVoteTally> {
  return apiPut<InitVoteTally, { content: string }>(`/api/collaborations/votes/init/${enc(initId)}`, { content });
}

export async function clearInitiativeVote(initId: number): Promise<InitVoteTally> {
  return apiDelete<InitVoteTally>(`/api/collaborations/votes/init/${enc(initId)}`);
}

// Requests / notifications — scoped to the caller by the API.

export async function getInitiativeRequests(state: "PENDING" | "HANDLED" = "PENDING"): Promise<InitiativeRequest[]> {
  return apiGet<InitiativeRequest[]>(`/api/collaborations/requests${buildQueryString({ state, limit: 200 })}`);
}

export async function getInitiativeNotifications(limit = 5): Promise<InitNotificationFeed> {
  return apiGet<InitNotificationFeed>(`/api/collaborations/notifications${buildQueryString({ limit })}`);
}

/** Acknowledge an ACCEPTANCE / REJECTION notice (records it as HANDLED). */
export async function acknowledgeCollaboration(id: number): Promise<Collaboration> {
  return apiPost<Collaboration, Record<string, never>>(`/api/collaborations/notifications/${enc(id)}/acknowledge`, {});
}
