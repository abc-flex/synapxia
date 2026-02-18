/**
 * Type definitions for Role entity
 */

export interface Role {
  code: string;
  name: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}
