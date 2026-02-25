/**
 * Type definitions for Assignment entity
 */

export interface Assignment {
  id?: number;
  team: string;
  user_id: number;
  role: string;
  observation?: string;
  valid_from?: string;
  valid_to?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}
