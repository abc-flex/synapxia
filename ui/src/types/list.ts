/**
 * Type definitions for List entity
 */

export interface List {
  id?: number;
  module: string;
  code: string;
  name: string;
  type: string;
  description?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}
