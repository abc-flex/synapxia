// Normalize an arbitrary date/datetime string into the value format native
// <input type="date" | "datetime-local"> expects: "YYYY-MM-DD" or
// "YYYY-MM-DDTHH:mm". ISO-ish strings are sliced (no timezone shift).
function normalizeCalendarValue(raw, withTime) {
  const s = (raw ?? "").toString().trim();
  if (!s) return "";
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, withTime ? 16 : 10);
  const d = new Date(s);
  if (isNaN(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  const date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  return withTime ? `${date}T${pad(d.getHours())}:${pad(d.getMinutes())}` : date;
}

export function initCrudPage({
  dataId,
  editModalId,
  deleteModalId,
  rowsAttr = "rows",
  keysAttr = "keys",
}) {
  if (typeof window === "undefined") return;

  const dataEl = document.getElementById(dataId);
  if (!dataEl) return;

  const encodedRows = dataEl.dataset?.[rowsAttr] || "%5B%5D";
  const encodedKeys = dataEl.dataset?.[keysAttr] || "%5B%5D";

  let rows = [];
  let keys = [];
  try {
    rows = JSON.parse(decodeURIComponent(encodedRows));
    keys = JSON.parse(decodeURIComponent(encodedKeys));
  } catch (err) {
    console.error(`Failed to decode ${dataId}`, err);
    return;
  }

  const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
  const editDialog = document.getElementById(editModalId);
  const deleteDialog = document.getElementById(deleteModalId);
  const createModalId = dataId.replace("-data", "-create-modal");
  const createDialog = document.getElementById(createModalId);

  const fillForm = (dialog, record) => {
    if (!dialog || !record) return;

    // Use multiple requestAnimationFrames to ensure dialog is fully rendered
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        // Set the hidden ID field
        const idInput = dialog.querySelector('[name="id"]');
        if (idInput && record.id) {
          idInput.value = record.id;
        }

        keys.forEach((key) => {
          const input = dialog.querySelector(`[name="${key}"]`);
          if (!input) {
            console.warn(`Input with name="${key}" not found in dialog`);
            return;
          }

          const value = record[key];

          if (input.type === "checkbox") {
            input.checked = Boolean(value);
          } else if (input.tagName === "SELECT") {
            // Handle select fields - try multiple matching strategies
            const selectOptions = input.querySelectorAll("option");
            let matched = false;

            // Strategy 1: Direct value match
            for (let option of selectOptions) {
              if (option.value === String(value)) {
                input.value = option.value;
                matched = true;
                break;
              }
            }

            // Strategy 2: If value is an object, try to match by common properties
            if (!matched && typeof value === "object" && value !== null) {
              const matchableProps = ["id", "code", "name", "value"];
              for (let prop of matchableProps) {
                const propValue = value[prop];
                if (propValue) {
                  for (let option of selectOptions) {
                    if (option.value === String(propValue)) {
                      input.value = option.value;
                      matched = true;
                      break;
                    }
                  }
                  if (matched) break;
                }
              }
            }

            // Fallback: just set the string value
            if (!matched) {
              input.value = String(value ?? "");
            }

            // Dispatch change event to trigger any listeners
            input.dispatchEvent(new Event("change", { bubbles: true }));
          } else if (input.tagName === "TEXTAREA") {
            input.value = String(value ?? "");
          } else if (input.type === "date" || input.type === "datetime-local") {
            // Native date pickers need "YYYY-MM-DD" / "YYYY-MM-DDTHH:mm".
            input.value = normalizeCalendarValue(value, input.type === "datetime-local");
          } else {
            input.value = String(value ?? "");
          }
        });
      });
    });
  };

  const clearForm = (dialog) => {
    if (!dialog) return;

    // Clear the hidden ID field
    const idInput = dialog.querySelector('[name="id"]');
    if (idInput) {
      idInput.value = "";
    }

    // Clear all form fields
    keys.forEach((key) => {
      const input = dialog.querySelector(`[name="${key}"]`);
      if (!input) return;
      
      if (input.type === "checkbox") {
        input.checked = false;
      } else if (input.tagName === "SELECT") {
        input.value = "";
        input.dispatchEvent(new Event("change", { bubbles: true }));
      } else {
        input.value = "";
      }
    });
  };

  const openDialog = (dialog) => {
    if (!dialog || dialog.open) return;
    dialog.showModal();
  };

  // Listen for create button clicks to clear the form
  document.addEventListener("click", (e) => {
    const createBtn = e.target.closest(`[data-modal-open="${createModalId}"]`);
    if (createBtn && createDialog) {
      clearForm(createDialog);
    }
  });

  document.addEventListener("datatable-action", (e) => {
    const detail = /** @type {CustomEvent} */ (e).detail || {};
    const { action, id } = detail;
    
    if (!id) {
      console.error("datatable-action: No ID provided");
      return;
    }

    const record = byId[id];
    if (!record) {
      console.error(`datatable-action: Record not found for ID: "${id}". Available IDs:`, Object.keys(byId));
      return;
    }

    if (action === "edit") {
      openDialog(editDialog);
      fillForm(editDialog, record);
    } else if (action === "delete") {
      openDialog(deleteDialog);
      fillForm(deleteDialog, record);
    }
  });
}
