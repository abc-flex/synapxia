/**
 * Type definitions for ListItem entity
 */

export interface ListItem {
  list: string;
  value: string;
  label: string;
  sort_order: number;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}
