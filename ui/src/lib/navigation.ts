import type { NavModule, NavOption } from "@/types/nav";
import { getModules } from "@/lib/modules";
import { getOptions } from "@/lib/options";

// Fetch modules and options from API once at module load
let modules: any[] = [];
let options: any[] = [];

try {
  modules = await getModules();
} catch (error) {
  console.error('Failed to fetch modules:', error);
  modules = [];
}

try {
  options = await getOptions();
} catch (error) {
  console.error('Failed to fetch options:', error);
  options = [];
}

export function getNavigationData() {
  const primaryNav: NavModule[] = modules.map((module) => ({
    code: module.code,
    name: module.name,
    icon: module.icon,
  }));

  const itemsNav: NavOption[] = options.map((option) => ({
    module: option.module,
    code: option.code,
    name: option.name,
    path: option.path,
  }));

  return { primaryNav, itemsNav };
}
