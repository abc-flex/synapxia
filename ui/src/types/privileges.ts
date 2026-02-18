/**
 * Type definitions for Privilege entity
 */

export interface Privilege {
  role: string;
  module: string;
  option: string;
  can_edit?: boolean;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}
