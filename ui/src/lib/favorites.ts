/**
 * Favorites API service.
 *
 * Composite-PK `(user_id, asset)` bookmark rows; `asset` is the asset id.
 *
 * Status-code semantics callers must handle:
 *   - GET 404 → never favorited; GET 400 → previously favorited but
 *     logically deleted. BOTH mean "not currently favorited".
 *   - POST 409 → an inactive row exists; fall back to
 *     `updateFavorite(userId, assetId, { is_active: true })` to reactivate.
 */

import { apiGet, apiPost, apiPut, apiDelete } from "./api";
import type { Favorite, FavoriteCreate, FavoriteUpdate } from "../types/api";

export async function getFavorite(
  userId: number,
  assetId: number,
): Promise<Favorite> {
  return apiGet<Favorite>(
    `/api/favorites/${encodeURIComponent(String(userId))}/${encodeURIComponent(String(assetId))}`,
  );
}

export async function createFavorite(data: FavoriteCreate): Promise<Favorite> {
  return apiPost<Favorite, FavoriteCreate>("/api/favorites/", data);
}

export async function updateFavorite(
  userId: number,
  assetId: number,
  data: FavoriteUpdate,
): Promise<Favorite> {
  return apiPut<Favorite, FavoriteUpdate>(
    `/api/favorites/${encodeURIComponent(String(userId))}/${encodeURIComponent(String(assetId))}`,
    data,
  );
}

export async function deleteFavorite(
  userId: number,
  assetId: number,
): Promise<Favorite> {
  return apiDelete<Favorite>(
    `/api/favorites/${encodeURIComponent(String(userId))}/${encodeURIComponent(String(assetId))}`,
  );
}

/**
 * Convenience: set the favorite bit for (user, asset) to `on`, handling all
 * the soft-delete / re-add edge cases in one call.
 */
export async function setFavorite(
  userId: number,
  assetId: number,
  on: boolean,
): Promise<void> {
  if (on) {
    try {
      await createFavorite({ user_id: userId, asset: assetId });
    } catch {
      // 409: inactive row exists → reactivate
      await updateFavorite(userId, assetId, { is_active: true });
    }
  } else {
    await deleteFavorite(userId, assetId);
  }
}

/** True when the user currently has the asset favorited (active row). */
export async function isFavorite(
  userId: number,
  assetId: number,
): Promise<boolean> {
  try {
    await getFavorite(userId, assetId);
    return true;
  } catch {
    return false; // 404 (never) and 400 (inactive) both mean "not favorited"
  }
}
