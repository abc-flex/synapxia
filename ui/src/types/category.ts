/**
 * Type definitions for Category entity
 */

export interface Category {
  code: string;
  name: string;
  description?: string;
  parent?: string;
  icon?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}
