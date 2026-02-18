/**
 * Type definitions for User entity
 */

export interface User {
  id?: number;
  username: string;
  email: string;
  password_hash: string;
  first_name: string;
  last_name: string;
  menu_role: string;
  business_unit: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
  last_login_at?: string;
}
