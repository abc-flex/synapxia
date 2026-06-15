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
  lang: string;
  value: string;
  label: string;
  sort_order: number;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ListItemCreate {
  list: string;
  lang: string;
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

// ItemTranslation types
export interface ItemTranslation  {
  list: string;
  value: string;
  lang: string;
  label: string;
  sort_order: number;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ItemTranslationCreate {
  list: string;
  value: string;
  label: string;
  sort_order: number;
  is_active?: boolean;
}

export interface ItemTranslationUpdate {
  label?: string;
  sort_order?: number;
  is_active?: boolean;
}

// Profile types
export interface Profile {
  code: string;
  name: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface ProfileCreate {
  code: string;
  name: string;
  description?: string;
  is_active?: boolean;
}

export interface ProfileUpdate {
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
  profile: string;
  unit: string;
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
  profile: string;
  unit: string;
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
  profile: string;
  unit: string;
  is_active?: boolean;
}

export interface UserUpdate {
  username?: string;
  email?: string;
  password?: string;
  first_name?: string;
  last_name?: string;
  profile?: string;
  unit?: string;
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

// Specification types
export interface Specification {
  category: string;
  feature: string;
  default_value: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface SpecificationCreate {
  category: string;
  feature: string;
  default_value: string;
  is_active?: boolean;
}

export interface SpecificationUpdate {
  default_value?: string;
  is_active?: boolean;
}

// Generic API Error
export interface ApiError {
  detail: string;
}

// Dimension types
export interface Dimension {
  code: string;
  name: string;
  description?: string;
  scale?: string;
  unit?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface DimensionCreate {
  code: string;
  name: string;
  description?: string;
  scale?: string;
  unit?: string;
  is_active?: boolean;
}

export interface DimensionUpdate {
  name?: string;
  description?: string;
  scale?: string;
  unit?: string;
  is_active?: boolean;
}

// Metric types
export interface Metric {
  id: number;
  dimension: string;
  assignment: number;
  value: string;
  observation?: string;
  measured_at: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface MetricCreate {
  dimension: string;
  assignment: number;
  value: string;
  observation?: string;
  measured_at?: string;
  is_active?: boolean;
}

export interface MetricUpdate {
  value?: string;
  observation?: string;
  measured_at?: string;
  is_active?: boolean;
}

// Team types
export interface Team {
  code: string;
  name: string;
  description?: string;
  lead?: number;
  chat_channel_url?: string;
  kanban_board_url?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface TeamCreate {
  code: string;
  name: string;
  description?: string;
  lead?: number;
  chat_channel_url?: string;
  kanban_board_url?: string;
  is_active?: boolean;
}

export interface TeamUpdate {
  name?: string;
  description?: string;
  lead?: number;
  chat_channel_url?: string;
  kanban_board_url?: string;
  is_active?: boolean;
}

// Role types
export interface Role {
  code: string;
  name: string;
  description?: string;
  icon?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface RoleCreate {
  code: string;
  name: string;
  description?: string;
  icon?: string;
  is_active?: boolean;
}

export interface RoleUpdate {
  name?: string;
  description?: string;
  icon?: string;
  is_active?: boolean;
}

// Assignment types
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

export interface AssignmentCreate {
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

export interface AssignmentUpdate {
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


// Asset types
export interface Asset {
  id?: number;
  name: string;
  description?: string;
  category?: string;
  reference?: string;
  status: string;
  tags?: string[];
  detail?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AssetCreate {
  name: string;
  description?: string;
  category?: string;
  reference?: string;
  status: string;
  tags?: string[];
  detail?: string;
  is_active?: boolean;
}

export interface AssetUpdate {
  name?: string;
  description?: string;
  category?: string;
  reference?: string;
  status?: string;
  tags?: string[];
  detail?: string;
  is_active?: boolean;
}

// ============================================================================
// Characterizations — composite-key (asset, feature) rows that hold the
// per-feature value for an asset (e.g. asset #3 + feature MODE → "Remote").
// ============================================================================

export interface Characterization {
  asset: number;
  feature: string;
  value?: string;
  detail?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CharacterizationCreate {
  asset: number;
  feature: string;
  value?: string;
  detail?: string;
  is_active?: boolean;
}

export interface CharacterizationUpdate {
  value?: string;
  detail?: string;
  is_active?: boolean;
}

// ============================================================================
// Asset relations — composite-key (source, target) rows linking two assets
// with a typed relationship (RELATION_TYPE list) + optional rationale.
// Both source and target are asset ids (assets.id).
// ============================================================================

export interface AssetRelation {
  source: number;
  target: number;
  type: string;
  rationale?: string | null;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AssetRelationCreate {
  source: number;
  target: number;
  type: string;
  rationale?: string;
  is_active?: boolean;
}

export interface AssetRelationUpdate {
  type?: string;
  rationale?: string | null;
  is_active?: boolean;
}

// ============================================================================
// Asset permissions — surrogate-id rows granting a target (USER/ROLE/TEAM/
// UNIT/PROJECT/PUBLIC × access level) access to an asset. `asset` is the
// asset id; `target_code` is the target entity's id/code ("PUBLIC" for PUBLIC).
// ============================================================================

export interface AssetPermission {
  id: number;
  asset: number;
  target_type: string;
  target_code: string;
  access_level: string;
  valid_from?: string;
  valid_to?: string | null;
  is_active?: boolean;
}

export interface AssetPermissionCreate {
  asset: number;
  target_type: string;
  target_code: string;
  access_level: string;
  valid_to?: string | null;
  is_active?: boolean;
}

export interface AssetPermissionUpdate {
  target_type?: string;
  target_code?: string;
  access_level?: string;
  valid_to?: string | null;
  is_active?: boolean;
}

// ============================================================================
// Favorites — composite-key (user_id, asset) bookmark rows. `asset` is the
// asset id (assets.id).
// ============================================================================

export interface Favorite {
  user_id: number;
  asset: number;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface FavoriteCreate {
  user_id: number;
  asset: number;
  is_active?: boolean;
}

export interface FavoriteUpdate {
  is_active?: boolean;
}
