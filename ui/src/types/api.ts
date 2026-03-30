/**
 * API Type Definitions
 * Type definitions for API requests and responses
 */

// Module types
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

export interface ModuleCreate {
  code: string;
  name: string;
  description?: string;
  sort_order?: number;
  icon?: string;
  is_active?: boolean;
}

export interface ModuleUpdate {
  name?: string;
  description?: string;
  sort_order?: number;
  icon?: string;
  is_active?: boolean;
}

// BusinessUnit types
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

export interface BusinessUnitCreate {
  code: string;
  name: string;
  description?: string;
  type: string;
  parent: string;
  is_active?: boolean;
}

export interface BusinessUnitUpdate {
  name?: string;
  description?: string;
  type?: string;
  parent?: string;
  is_active?: boolean;
}

// List types
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

export interface ListCreate {
  module: string;
  code: string;
  name: string;
  type: string;
  description?: string;
  is_active?: boolean;
}

export interface ListUpdate {
  name?: string;
  type?: string;
  description?: string;
  is_active?: boolean;
}

// ListItem types
export interface ListItem  {
  list: string;
  value: string;
  label: string;
  sort_order: number;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ListItemCreate {
  list: string;
  value: string;
  label: string;
  sort_order: number;
  is_active?: boolean;
}

export interface ListItemUpdate {
  label?: string;
  sort_order?: number;
  is_active?: boolean;
}

// Role types
export interface Role {
  code: string;
  name: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface RoleCreate {
  code: string;
  name: string;
  description?: string;
  is_active?: boolean;
}

export interface RoleUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
}

// User types
export interface UserRead {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  menu_role: string;
  business_unit: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  last_login_at?: string;
}

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

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  menu_role: string;
  business_unit: string;
  is_active?: boolean;
}

export interface UserUpdate {
  username?: string;
  email?: string;
  password?: string;
  first_name?: string;
  last_name?: string;
  menu_role?: string;
  business_unit?: string;
  is_active?: boolean;
}

// Authentication types
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserRead;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

export interface ChangePasswordResponse {
  message: string;
}

// Option types
export interface Option {
  module: string;
  code: string;
  name: string;
  path?: string;
  type: string;
  sort_order: number;
  description?: string;
  icon?: string;
  is_active: boolean;
}

export interface OptionCreate {
  module: string;
  code: string;
  name: string;
  path?: string;
  type: string;
  sort_order?: number;
  description?: string;
  icon?: string;
  is_active?: boolean;
}

export interface OptionUpdate {
  name?: string;
  path?: string;
  type?: string;
  sort_order?: number;
  description?: string;
  icon?: string;
  is_active?: boolean;
}

// Project types
export interface Project {
  code: string;
  name: string;
  description?: string;
  team?: string;
  repo_url?: string;
  status: string;
  start_date?: string;
  end_date?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface ProjectCreate {
  code: string;
  name: string;
  description?: string;
  team?: string;
  repo_url?: string;
  status: string;
  start_date?: string;
  end_date?: string;
  is_active?: boolean;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  team?: string;
  repo_url?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  is_active?: boolean;
}

// Privilege types
export interface Privilege {
  role: string;
  module: string;
  option: string;
  can_edit?: boolean;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface PrivilegeCreate {
  role: string;
  module: string;
  option: string;
  can_edit?: boolean;
  is_active?: boolean;
}

export interface PrivilegeUpdate {
  can_edit?: boolean;
  is_active?: boolean;
}

// Category types
export interface Category {
  code: string;
  name: string;
  description?: string;
  parent?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CategoryCreate {
  code: string;
  name: string;
  description?: string;
  parent?: string;
  is_active?: boolean;
}

export interface CategoryUpdate {
  name?: string;
  description?: string;
  parent?: string;
  is_active?: boolean;
}

// Feature types
export interface Feature {
  code: string;
  name: string;
  description?: string;
  type: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface FeatureCreate {
  code: string;
  name: string;
  description?: string;
  type: string;
  is_active?: boolean;
}

export interface FeatureUpdate {
  name?: string;
  description?: string;
  type?: string;
  is_active?: boolean;
}

// Generic API Error
export interface ApiError {
  detail: string;
}
