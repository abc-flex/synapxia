/**
 * Type definitions for BusinessUnit entity
 */

export interface BusinessUnit {
  code: string;
  name: string;
  description?: string;
  type: string;
  parent: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}
