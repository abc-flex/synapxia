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

    // Set the hidden ID field
    const idInput = dialog.querySelector('[name="id"]');
    if (idInput && record.id) {
      idInput.value = record.id;
    }

    keys.forEach((key) => {
      const input = dialog.querySelector(`[name="${key}"]`);
      if (!input) return;
      if (input.type === "checkbox") {
        input.checked = Boolean(record[key]);
      } else {
        input.value = record[key] ?? "";
      }
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
    const record = id ? byId[id] : null;
    if (!record) return;

    if (action === "edit") {
      fillForm(editDialog, record);
      openDialog(editDialog);
    }

    if (action === "delete") {
      fillForm(deleteDialog, record);
      openDialog(deleteDialog);
    }
  });
}
