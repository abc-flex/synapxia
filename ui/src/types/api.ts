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

// Profile types
export interface Profile {
  code: string;
  name: string;
  description?: string;
  icon?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface ProfileCreate {
  code: string;
  name: string;
  description?: string;
  icon?: string;
  is_active?: boolean;
}

export interface ProfileUpdate {
  name?: string;
  description?: string;
  icon?: string;
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
  detail?: string;
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
  detail?: string;
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
  detail?: string;
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
  icon?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CategoryCreate {
  code: string;
  name: string;
  description?: string;
  parent?: string;
  icon?: string;
  is_active?: boolean;
}

export interface CategoryUpdate {
  name?: string;
  description?: string;
  parent?: string;
  icon?: string;
  is_active?: boolean;
}

// Feature types
export interface Feature {
  code: string;
  name: string;
  description?: string;
  type: string;
  list?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface FeatureCreate {
  code: string;
  name: string;
  description?: string;
  type: string;
  list?: string;
  is_active?: boolean;
}

export interface FeatureUpdate {
  name?: string;
  description?: string;
  type?: string;
  list?: string;
  is_active?: boolean;
}

// Specification types
export interface Specification {
  category: string;
  feature: string;
  default_value?: string | null;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface SpecificationCreate {
  category: string;
  feature: string;
  default_value?: string | null;
  is_active?: boolean;
}

export interface SpecificationUpdate {
  default_value?: string | null;
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

// Latest metric value per assignment for a dimension, as of a date.
// Read-only projection returned by GET /api/metrics/dimension/{code}.
export interface MetricByDimension {
  name: string;
  email: string;
  role: string;
  team: string;
  metric: string;
  date: string;
  observation: string;
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

// Propose (HU-Propose): request body for proposing an asset for review.
// `reviewer_id` optional (auto-assigned when omitted); `values` optionally
// overrides the category specs' default characterization values (feature→value).
export interface ProposeRequest {
  name: string;
  description?: string;
  category: string;
  reference?: string;
  tags?: string[];
  detail?: string;
  reviewer_id?: number;
  values?: Record<string, string>;
}

// A selectable reviewer for the propose form ({value: id, label: name}).
export interface ReviewerOption {
  value: number;
  label: string;
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

// Read projection from GET /api/assets/with-access: Asset + aggregated access summary.
export interface AssetWithAccessLevels extends Asset {
  access_levels: string[]; // distinct active access levels, e.g. ["VIEW","MANAGE"]
  is_public: boolean;       // true if any active permission targets PUBLIC
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

// Read projection (HU-LI07) for the gallery "Related" section: a related asset
// resolved from `related_assets` in either direction, carrying the relation
// metadata. `direction` is "outgoing" when the viewed asset is the relation's
// source (it references this one) and "incoming" when it is the target.
export interface RelatedAsset {
  id: number;
  name: string;
  description?: string | null;
  category?: string | null;
  status: string;
  tags?: unknown;
  relation_type: string;
  direction: "outgoing" | "incoming";
  rationale?: string | null;
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

// ============================================================================
// Actions — the generic `actions` event log. Every asset interaction (votes,
// comments, questions, answers) and review-workflow step is a row here; the
// `type` field discriminates. No per-feature table.
// ============================================================================

export interface Action {
  id?: number;
  asset: number;
  user_id: number;
  type: string;
  workflow_status?: string;
  content?: string;
  reference?: string;
  parent?: number;
  detail?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ActionCreate {
  asset: number;
  user_id: number;
  type: string;
  workflow_status?: string;
  content?: string;
  reference?: string;
  parent?: number;
  detail?: string;
  is_active?: boolean;
}

export interface ActionUpdate {
  workflow_status?: string;
  content?: string;
  reference?: string;
  parent?: number;
  detail?: string;
  is_active?: boolean;
}

// Aggregated vote summary for an asset (HU-LI05). Votes are `actions` of type
// VOTE with content POSITIVE/NEGATIVE; `my_vote` is the requester's own vote.
export interface VoteTally {
  asset: number;
  positive: number;
  negative: number;
  score: number;
  my_vote?: string | null;
}

// Foro (HU-LI06) — comments/questions/answers are `actions` of type
// COMMENT/QUESTION/ANSWER; an answer threads to its question via `parent`.
// `DiscussionItem` is the read shape (author username resolved server-side).
export interface DiscussionItem {
  id: number;
  asset: number;
  user_id: number;
  author?: string | null;
  type: "COMMENT" | "QUESTION" | "ANSWER";
  content?: string | null;
  parent?: number | null;
  created_at: string;
}

export interface ParticipationCreate {
  user_id: number;
  asset: number;
  content: string;
}

export interface AnswerCreate extends ParticipationCreate {
  parent: number;
}

// History timeline entry (HU-LI10): one event in an asset's activity log —
// an `actions` row (vote/comment/question/answer/workflow) or the synthetic
// CREATED marker (`id` null). `summary` is the server fallback label; the UI
// localizes by `type`. `content` is present only for COMMENT/QUESTION/ANSWER.
export interface HistoryEntry {
  id: number | null;
  type: string;
  actor?: string | null;
  summary: string;
  content?: string | null;
  workflow_status?: string | null;
  created_at: string;
}

// Workflow notification (HU-LI11): the latest row of a per-(asset,type)
// assignment thread directed at the current user. `unread` is true while it is
// still ASSIGNED (shown bold); NOTIFIED items are seen and dismissible. `id` is
// that latest action's id, used to advance the thread (notified/dismiss).
export interface NotificationItem {
  id: number;
  asset: number;
  asset_name?: string | null;
  type: string;
  workflow_status: string;
  unread: boolean;
  created_at: string;
}

// Criteria types
export interface Criteria {
  code: string;
  name: string;
  description?: string;
  list?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface CriteriaCreate {
  code: string;
  name: string;
  description?: string;
  list?: string;
  is_active?: boolean;
}

export interface CriteriaUpdate {
  name?: string;
  description?: string;
  list?: string;
  is_active?: boolean;
}
