/**
 * API Type Definitions
 * Type definitions for API requests and responses
 */

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

// Generic API Error
export interface ApiError {
  detail: string;
}
