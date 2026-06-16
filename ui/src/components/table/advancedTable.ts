import { ui } from "@/i18n";

export function initAdvancedTable(
    tableId: string,
    data: Record<string, any>[],
    allColumns: { key: string; label: string; visible?: boolean }[],
    visibleColumns: { key: string; label: string; visible?: boolean }[] = [],
    columnFilter: string | null = null,
    columnFilter2: string | null = null,
    filterDefaultValue: string = "",
    filterDefaultValue2: string = "",
    columnFilter3: string | null = null,
    filterDefaultValue3: string = "",
    columnFilter4: string | null = null,
    filterDefaultValue4: string = ""
) {
    // Normalize a value for filter comparison: strip a leading `N-` ordinal
    // prefix so a bare seeded code (e.g. `IN_USE`) matches the prefixed
    // list_items.value the dropdown carries (e.g. `6-IN_USE`). No-op for
    // codes without a prefix (categories, favorite "yes"/"no").
    const normFilter = (v: unknown): string => String(v ?? "").replace(/^\d+-/, "");

    // Remove any open master-detail expansion rows. Called before every
    // re-render (filter/search/paginate) so injected `[data-detail-row]`
    // siblings never throw off the data[rowIndex] alignment or pagination
    // counts (which assume one <tr> per data row).
    const purgeDetailRows = () => {
        document
            .querySelectorAll(`#${tableId} tbody tr[data-detail-row]`)
            .forEach((r) => r.remove());
    };
    // Si visibleColumns no se pasa o está vacío, usar allColumns como fallback
    const columns = visibleColumns.length > 0 ? visibleColumns : allColumns;

    let currentPage = 1;
    let perPage = 10;

    // Get current locale from localStorage or default to 'en'
    const getCurrentLocale = (): 'en' | 'es' => {
        const stored = localStorage.getItem("lang");
        return (stored === 'es' || stored === 'en') ? stored : 'en';
    };

    // Helper to get nested translation value
    const t = (key: string): string => {
        const locale = getCurrentLocale();
        const keys = key.split('.');
        let value: any = ui[locale];
        for (const k of keys) {
            value = value?.[k];
            if (value === undefined) return key;
        }
        return value ?? key;
    };

    const table = document.getElementById(tableId) as HTMLTableElement | null;
    if (!table) return;

    const tbody = table.querySelector("tbody");
    if (!tbody) return;

    /* ======================
       SEARCH
    ====================== */
    const searchInput = document.getElementById(
        `${tableId}-search`
    ) as HTMLInputElement | null;

    if (searchInput) {
        searchInput.addEventListener("input", () => {
            applyFilters();
        });
    }

    /* ======================
       COLUMN FILTER (up to two filters, AND-combined)
    ====================== */
    const filterSelect = document.getElementById(
        `${tableId}-filter`
    ) as HTMLSelectElement | null;
    const filterSelect2 = document.getElementById(
        `${tableId}-filter2`
    ) as HTMLSelectElement | null;
    const filterSelect3 = document.getElementById(
        `${tableId}-filter3`
    ) as HTMLSelectElement | null;
    const filterSelect4 = document.getElementById(
        `${tableId}-filter4`
    ) as HTMLSelectElement | null;

    let filterKey: string | null = null;
    let filterKey2: string | null = null;
    let filterKey3: string | null = null;
    let filterKey4: string | null = null;

    /* ======================
       RESET FILTERS
       Clears search + every filter select; shown only when something is active.
       Declared before the filter-init blocks because those call applyFilters()
       on load, and applyFilters() calls updateResetVisibility().
    ====================== */
    const resetBtn = document.getElementById(`${tableId}-reset`);

    const isFilterActive = (): boolean =>
        Boolean(
            (searchInput?.value ?? "") ||
            (filterSelect?.value ?? "") ||
            (filterSelect2?.value ?? "") ||
            (filterSelect3?.value ?? "") ||
            (filterSelect4?.value ?? "")
        );

    const updateResetVisibility = () => {
        if (!resetBtn) return;
        resetBtn.classList.toggle("hidden", !isFilterActive());
    };

    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            if (searchInput) searchInput.value = "";
            if (filterSelect) filterSelect.value = "";
            if (filterSelect2) filterSelect2.value = "";
            if (filterSelect3) filterSelect3.value = "";
            if (filterSelect4) filterSelect4.value = "";
            applyFilters();
        });
    }

    if (filterSelect) {
        filterKey = filterSelect.dataset.columnKey ?? null;

        // 🔹 Obtener valor inicial desde URL; si no, usar el valor por defecto
        const urlParams = new URLSearchParams(window.location.search);
        const filterParam = columnFilter ? urlParams.get(columnFilter) : null;
        const initialValue = filterParam ?? filterDefaultValue;
        if (initialValue) {
            filterSelect.value = initialValue;
        }

        filterSelect.addEventListener("change", () => {
            applyFilters();
        });

        if (initialValue) {
            applyFilters();
        }
    }

    if (filterSelect2) {
        filterKey2 = filterSelect2.dataset.columnKey ?? null;

        const urlParams = new URLSearchParams(window.location.search);
        const filterParam2 = columnFilter2 ? urlParams.get(columnFilter2) : null;
        const initialValue2 = filterParam2 ?? filterDefaultValue2;
        if (initialValue2) {
            filterSelect2.value = initialValue2;
        }

        filterSelect2.addEventListener("change", () => {
            applyFilters();
        });

        if (initialValue2) {
            applyFilters();
        }
    }

    if (filterSelect3) {
        filterKey3 = filterSelect3.dataset.columnKey ?? null;

        const urlParams = new URLSearchParams(window.location.search);
        const filterParam3 = columnFilter3 ? urlParams.get(columnFilter3) : null;
        const initialValue3 = filterParam3 ?? filterDefaultValue3;
        if (initialValue3) {
            filterSelect3.value = initialValue3;
        }

        filterSelect3.addEventListener("change", () => {
            applyFilters();
        });

        if (initialValue3) {
            applyFilters();
        }
    }

    if (filterSelect4) {
        filterKey4 = filterSelect4.dataset.columnKey ?? null;

        const urlParams = new URLSearchParams(window.location.search);
        const filterParam4 = columnFilter4 ? urlParams.get(columnFilter4) : null;
        const initialValue4 = filterParam4 ?? filterDefaultValue4;
        if (initialValue4) {
            filterSelect4.value = initialValue4;
        }

        filterSelect4.addEventListener("change", () => {
            applyFilters();
        });

        if (initialValue4) {
            applyFilters();
        }
    }

    // Reflect initial state (e.g. a filterDefaultValue applied above, or none).
    updateResetVisibility();

    /* ======================
       FILTRO COMBINADO
    ====================== */
    function applyFilters() {
        // Collapse any open detail-expansion rows first so the index/data
        // alignment below stays 1:1 with `data`.
        purgeDetailRows();

        const searchTerm = searchInput?.value.toLowerCase() ?? "";
        const filterValue = filterSelect?.value ?? "";
        const filterValue2 = filterSelect2?.value ?? "";
        const filterValue3 = filterSelect3?.value ?? "";
        const filterValue4 = filterSelect4?.value ?? "";

        const rows = Array.from(tbody.querySelectorAll("tr")) as HTMLTableRowElement[];

        rows.forEach((row, rowIndex) => {
            let visible = true;
            const rowData = data[rowIndex];

            // 🔍 Search global
            if (searchTerm) {
                const text = row.textContent?.toLowerCase() ?? "";
                visible = visible && text.includes(searchTerm);
            }

            // 🏷️ Filtro por columna (búsqueda en los datos, no en el DOM).
            // Prefix-normalized so e.g. status "IN_USE" matches "6-IN_USE".
            if (filterValue && filterKey && rowData) {
                const cellValue = String(rowData[filterKey] ?? "");
                visible = visible && normFilter(cellValue) === normFilter(filterValue);
            }

            // 🏷️ Segundo filtro (AND con el primero)
            if (filterValue2 && filterKey2 && rowData) {
                const cellValue2 = String(rowData[filterKey2] ?? "");
                visible = visible && normFilter(cellValue2) === normFilter(filterValue2);
            }

            // 🏷️ Tercer filtro (AND) — e.g. favorites ("yes"/"no").
            if (filterValue3 && filterKey3 && rowData) {
                const cellValue3 = String(rowData[filterKey3] ?? "");
                visible = visible && normFilter(cellValue3) === normFilter(filterValue3);
            }

            // 🏷️ Cuarto filtro (AND) — membership match: the cell may hold a
            // comma-separated multi-value field (e.g. access "VIEW,MANAGE,PUBLIC").
            // A single-token field still matches (superset of exact equality).
            if (filterValue4 && filterKey4 && rowData) {
                const tokens = String(rowData[filterKey4] ?? "")
                    .split(",")
                    .map((s) => normFilter(s.trim()))
                    .filter(Boolean);
                visible = visible && tokens.includes(normFilter(filterValue4));
            }

            row.classList.toggle("hidden-by-filter", !visible);
        });
        currentPage = 1;
        renderPagination();
        updateResetVisibility();
    }

    /* ======================
       UTIL
    ====================== */
    function getColumnIndex(key: string): number {
        // First try to match by data-column-key attribute
        const headers = table.querySelectorAll("thead th");
        for (let i = 0; i < headers.length; i++) {
            if (headers[i].getAttribute("data-column-key") === key) {
                return i;
            }
        }
        // Fallback: match by column position in the columns array
        const columnIndex = columns.findIndex(col => col.key === key);
        return columnIndex !== -1 ? columnIndex : -1;
    }

    /* ======================
     EXPORT DROPDOWN
    ====================== */
    const exportBtn = document.getElementById(`${tableId}-export-btn`);
    const exportMenu = document.getElementById(`${tableId}-export-menu`);

    if (exportBtn && exportMenu) {
        exportBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            exportMenu.classList.toggle("hidden");
        });

        document.addEventListener("click", () => {
            exportMenu.classList.add("hidden");
        });
    }

    /* ======================
    EXPORT ACTIONS
    ====================== */
    //const exportMenu = document.getElementById(`${tableId}-export-menu`);

    if (exportMenu) {
        exportMenu.addEventListener("click", (e) => {
            const btn = (e.target as HTMLElement).closest<HTMLButtonElement>(
                "[data-export]"
            );
            if (!btn) return;

            const type = btn.dataset.export;
            if (!type) return;

            switch (type) {
                case "csv":
                    downloadFile(
                        toCSV(data, columns),
                        `${tableId}.csv`,
                        "text/csv"
                    );
                    break;

                case "json":
                    downloadFile(
                        JSON.stringify(data, null, 2),
                        `${tableId}.json`,
                        "application/json"
                    );
                    break;

                case "txt":
                    downloadFile(
                        toTXT(data, columns),
                        `${tableId}.txt`,
                        "text/plain"
                    );
                    break;

                case "sql":
                    downloadFile(
                        toSQL(data, columns),
                        `${tableId}.sql`,
                        "application/sql"
                    );
                    break;
            }
        });
    }

    function getVisibleRows(): HTMLTableRowElement[] {
        const rows = Array.from(
            table.querySelectorAll<HTMLTableRowElement>("tbody tr")
        );
        return rows.filter(row => !row.classList.contains("hidden-by-filter"));
    }

    function renderPagination() {
        const allRows = Array.from(
            table.querySelectorAll<HTMLTableRowElement>("tbody tr")
        );

        // 🔹 SOLO filas que pasan el filtro
        const filteredRows = allRows.filter(
            (row) => !row.classList.contains("hidden-by-filter")
        );

        const total = filteredRows.length;
        const totalPages = Math.ceil(total / perPage) || 1;

        if (currentPage > totalPages) {
            currentPage = totalPages;
        }

        const start = (currentPage - 1) * perPage;
        const end = start + perPage;

        // 🔹 Primero ocultar TODAS
        allRows.forEach((row) => {
            row.classList.add("hidden");
        });

        // 🔹 Mostrar solo las filas visibles de esta página
        filteredRows.slice(start, end).forEach((row) => {
            row.classList.remove("hidden");
        });

        // 🔹 Info
        const info = document.getElementById(`${tableId}-pagination-info`);
        if (info) {
            if (total === 0) {
                info.textContent = t("data_table.no_results");
                info.setAttribute("data-i18n", "data_table.no_results");

            } else {
                // Build structured HTML with separate translatable elements
                info.innerHTML = `
                    <span data-i18n="data_table.showing">${t("data_table.showing")}</span>
                    <span>${start + 1}–${Math.min(end, total)}</span>
                    <span data-i18n="data_table.of">${t("data_table.of")}</span>
                    <span>${total}</span>
                `;
                info.removeAttribute("data-i18n");

            }
        }

        // 🔹 Pages
        const pages = document.getElementById(`${tableId}-pages`);
        if (pages) {
            pages.innerHTML = "";

            for (let i = 1; i <= totalPages; i++) {
                const btn = document.createElement("button");
                btn.textContent = String(i);
                btn.className =
                    "px-3 py-1 text-sm rounded " +
                    (i === currentPage
                        ? "bg-indigo-600 text-white"
                        : "border border-gray-300 text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800");

                btn.addEventListener("click", () => {
                    currentPage = i;
                    renderPagination();
                });

                pages.appendChild(btn);
            }
        }

        // 🔹 Update prev/next button states
        const prevBtn = document.getElementById(`${tableId}-prev`);
        const nextBtn = document.getElementById(`${tableId}-next`);

        if (prevBtn) {
            if (currentPage === 1) {
                prevBtn.disabled = true;
                prevBtn.classList.add("opacity-50", "cursor-not-allowed");
            } else {
                prevBtn.disabled = false;
                prevBtn.classList.remove("opacity-50", "cursor-not-allowed");
            }
        }

        if (nextBtn) {
            if (currentPage === totalPages) {
                nextBtn.disabled = true;
                nextBtn.classList.add("opacity-50", "cursor-not-allowed");
            } else {
                nextBtn.disabled = false;
                nextBtn.classList.remove("opacity-50", "cursor-not-allowed");
            }
        }
    }

    document
        .getElementById(`${tableId}-prev`)
        ?.addEventListener("click", () => {
            if (currentPage > 1) {
                currentPage--;
                renderPagination();
            }
        });

    document
        .getElementById(`${tableId}-next`)
        ?.addEventListener("click", () => {
            const totalPages = Math.ceil(
                getVisibleRows().length / perPage
            ) || 1;
            if (currentPage < totalPages) {
                currentPage++;
                renderPagination();
            }
        });

    const perPageSelect = document.getElementById(
        `${tableId}-per-page`
    ) as HTMLSelectElement | null;

    if (perPageSelect) {
        perPageSelect.addEventListener("change", () => {
            perPage = Number(perPageSelect.value);
            currentPage = 1;
            renderPagination();
        });
    }

    /* ======================
       EDIT/DELETE ACTIONS
    ====================== */
    // Event delegation for edit and delete buttons within this table
    table.addEventListener("click", (e) => {
        const button = (e.target as HTMLElement).closest("[data-action]") as HTMLElement;
        if (!button) return;

        const action = button.dataset.action;
        const id = button.dataset.id;

        if (action && id) {
            // Dispatch custom event for CRUD operations
            document.dispatchEvent(
                new CustomEvent("datatable-action", {
                    detail: { action, id },
                })
            );
        }
    });

    // 🔹 Aplicar filtros iniciales después de renderizar
    applyFilters();

}

function toCSV(
    data: Record<string, any>[],
    columns: { key: string; label: string }[]
): string {
    const header = columns.map(c => `"${c.label}"`).join(",");

    const rows = data.map(row =>
        columns
            .map(c => `"${row[c.key] ?? ""}"`)
            .join(",")
    );

    return [header, ...rows].join("\n");
}

function toTXT(
    data: Record<string, any>[],
    columns: { key: string; label: string }[]
): string {
    return data
        .map(row =>
            columns
                .map(c => `${c.label}: ${row[c.key] ?? ""}`)
                .join(" | ")
        )
        .join("\n");
}

function toSQL(
    data: Record<string, any>[],
    columns: { key: string; label: string }[]
): string {
    const cols = columns.map(c => c.key).join(", ");

    return data
        .map(row =>
            `INSERT INTO ${tableName()} (${cols}) VALUES (${columns
                .map(c => `'${String(row[c.key] ?? "").replace(/'/g, "''")}'`)
                .join(", ")});`
        )
        .join("\n");
}

function tableName() {
    return "table_name";
}

function downloadFile(content: string, filename: string, type: string) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();

    URL.revokeObjectURL(url);
}

