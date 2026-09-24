/**
 * Initiative collaborations — read side (History timeline + Discussion thread)
 * for Initiative Management. Same response shapes as the asset readers, so the
 * shared `mountHistory` controller and the `Foro` island render them unchanged.
 */
import { apiGet, buildQueryString } from "./api";
import type { DiscussionItem, HistoryEntry, InitDiscussionItem } from "@/types/api";

const enc = (v: number) => encodeURIComponent(String(v));

export async function getInitiativeHistory(initId: number, skip = 0, limit = 200): Promise<HistoryEntry[]> {
  return apiGet<HistoryEntry[]>(
    `/api/collaborations/history/init/${enc(initId)}${buildQueryString({ skip, limit })}`,
  );
}

/** The thread in the `DiscussionItem` shape Foro expects (`init` → `asset`
 *  slot, which Foro only uses as an opaque key). */
export async function getInitiativeDiscussion(initId: number): Promise<DiscussionItem[]> {
  const rows = await apiGet<InitDiscussionItem[]>(`/api/collaborations/discussion/init/${enc(initId)}`);
  return rows.map(({ init, ...rest }) => ({ ...rest, asset: init }));
}
