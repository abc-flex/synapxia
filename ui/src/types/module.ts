/**
 * Type definitions for Module entity
 */

export interface Module {
  code: string;
  name: string;
  description?: string;
  sort_order: number;
  icon?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}
