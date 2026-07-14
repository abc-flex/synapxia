export interface NavModule {
  code: string;
  name: string;
  icon: string;
}

export interface NavOption {
  module: string;
  code: string;
  name: string;
  path: string;
  icon?: string | null;
}
