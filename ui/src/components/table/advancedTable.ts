import { ui } from "@/i18n";

export function initAdvancedTable(
    tableId: string,
    data: Record<string, any>[],
    columns: { key: string; label: string }[],
    columnFilter: string | null = null
) {

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
       COLUMN FILTER
    ====================== */
    const filterSelect = document.getElementById(
        `${tableId}-filter`
    ) as HTMLSelectElement | null;

    let filterKey: string | null = null;

    if (filterSelect) {
        filterKey = filterSelect.dataset.columnKey ?? null;

        // 🔹 Obtener valor inicial desde URL
        const urlParams = new URLSearchParams(window.location.search);
        const filterParam = columnFilter
            ? urlParams.get(columnFilter)
            : null;
        if (filterParam) {
            filterSelect.value = filterParam;
        }

        filterSelect.addEventListener("change", () => {
            applyFilters();
        });

        // Apply initial filter from URL param on page load
        if (filterParam) {
            applyFilters();
        }
    }

    /* ======================
       FILTRO COMBINADO
    ====================== */
    function applyFilters() {
        const searchTerm = searchInput?.value.toLowerCase() ?? "";
        const filterValue = filterSelect?.value ?? "";

        tbody.querySelectorAll("tr").forEach(row => {
            let visible = true;

            // 🔍 Search global
            if (searchTerm) {
                const text = row.textContent?.toLowerCase() ?? "";
                visible = visible && text.includes(searchTerm);
            }

            // 🏷️ Filtro por columna
            if (filterValue && filterKey) {
                const cellIndex = getColumnIndex(filterKey);
                if (cellIndex !== -1) {
                    const cellText =
                        row.children[cellIndex]?.textContent ?? "";
                    visible = visible && cellText === filterValue;
                }
            }

            row.classList.toggle("hidden-by-filter", !visible);
        });
        currentPage = 1;
        renderPagination();
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
                        : "border hover:bg-gray-100");

                btn.addEventListener("click", () => {
                    currentPage = i;
                    renderPagination();
                });

                pages.appendChild(btn);
            }
        }
    }

    document
        .getElementById(`${tableId}-prev`)
        ?.addEventListener("click", () => {
            currentPage--;
            renderPagination();
        });

    document
        .getElementById(`${tableId}-next`)
        ?.addEventListener("click", () => {
            currentPage++;
            renderPagination();
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

