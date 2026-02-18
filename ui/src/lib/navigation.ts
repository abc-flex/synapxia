import type { NavModule, NavOption } from "@/types/nav";
import { getModules } from "@/lib/modules";
import { getOptions } from "@/lib/options";

// Fetch modules and options from API
let modules: any[] = [];
let options: any[] = [];
let errorMessage: string | null = null;

try {
  const apiModules = await getModules();
  modules = apiModules;
} catch (error) {
  console.error('Failed to fetch modules:', error);
  errorMessage = error instanceof Error ? error.message : 'Failed to fetch modules from API';
  // Fallback to empty array to still render the page
  modules = [];
}

try {
  const apiOptions = await getOptions();
  options = apiOptions;
} catch (error) {
  console.error('Failed to fetch options:', error);
  errorMessage = error instanceof Error ? error.message : 'Failed to fetch options from API';
  // Fallback to empty array to still render the page
  options = [];
}

export function getNavigationData() {
  const primaryNav: NavModule[] = modules.map((module) => ({
    code: module.code,
    name: module.name,
    icon: `/src/images/icons/${module.icon}.svg`,
  }));

  const itemsNav: NavOption[] = options.map((option) => ({
    module: option.module,
    code: option.code,
    name: option.name,
    path: option.path,
  }));

  return { primaryNav, itemsNav };
}
