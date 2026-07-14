/**
 * Generic flat-to-tree builder for the treeview components.
 *
 * Works with any model that has an id field, a parent-reference field, and a
 * label field — the field names are configurable via `TreeFieldKeys`, so the
 * components are not tied to the `Category` model.
 */

export interface TreeFieldKeys {
  /** Unique identifier field. Default: `code`. */
  idKey: string;
  /** Parent reference field (holds another item's id). Default: `parent`. */
  parentKey: string;
  /** Display label field. Default: `name`. */
  labelKey: string;
  /** Optional secondary text field (shown under the label / in tooltips). Default: `description`. */
  descriptionKey?: string;
}

export const DEFAULT_TREE_KEYS: TreeFieldKeys = {
  idKey: 'code',
  parentKey: 'parent',
  labelKey: 'name',
  descriptionKey: 'description',
};

/** Normalized tree node consumed by the treeview components. */
export interface TreeNodeData {
  id: string;
  label: string;
  description: string;
  children: TreeNodeData[];
  /** Original item, kept for custom rendering / tooltips. */
  raw: Record<string, any>;
}

/**
 * Build a nested tree from a flat list of items.
 *
 * Items whose parent reference is empty — or points to an id not present in the
 * list — are treated as roots.
 */
export function buildTree(
  items: Record<string, any>[],
  keys: Partial<TreeFieldKeys> = {},
): TreeNodeData[] {
  const k = { ...DEFAULT_TREE_KEYS, ...keys };
  const byId = new Map<string, Record<string, any>>();
  const childrenMap = new Map<string, Record<string, any>[]>();

  items.forEach(item => {
    const id = String(item[k.idKey]);
    byId.set(id, item);
    if (!childrenMap.has(id)) childrenMap.set(id, []);
  });

  items.forEach(item => {
    const parent = item[k.parentKey];
    if (parent != null && parent !== '' && byId.has(String(parent))) {
      childrenMap.get(String(parent))!.push(item);
    }
  });

  const roots = items.filter(item => {
    const parent = item[k.parentKey];
    return parent == null || parent === '' || !byId.has(String(parent));
  });

  const toNode = (item: Record<string, any>): TreeNodeData => {
    const id = String(item[k.idKey]);
    return {
      id,
      label: String(item[k.labelKey] ?? ''),
      description: k.descriptionKey ? String(item[k.descriptionKey] ?? '') : '',
      children: (childrenMap.get(id) || []).map(toNode),
      raw: item,
    };
  };

  return roots.map(toNode);
}
