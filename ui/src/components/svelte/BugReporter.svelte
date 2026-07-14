<script lang="ts">
  /**
   * BugReporter — global floating "report a bug" widget (Svelte 5 island).
   * Self-mounted once from BugReportWidget.astro into BaseLayout, so the FAB
   * shows on every authenticated page. Also binds any `[data-bug-report-open]`
   * trigger already in the DOM at mount time (e.g. the /support page button).
   *
   * Flow: capture a screenshot of the current page (html2canvas, downscaled to
   * a JPEG data-URL), draw over it on a <canvas> (freehand pen / rectangle,
   * red stroke, undo/clear), optionally attach a few extra images, describe
   * the bug, submit. Screenshot/attachments travel as base64 data-URLs — the
   * backend caps size/count (see api/app/support/internal/models.py).
   */
  import { onMount, tick } from "svelte";
  import html2canvas from "html2canvas";
  import { createBugReport } from "@/lib/support";
  import { showToast } from "@/lib/toast";
  import { translate } from "@/utils/i18nClient";

  const MAX_ATTACHMENTS = 3;
  const SCREENSHOT_MAX_WIDTH = 1280;
  const ATTACHMENT_MAX_WIDTH = 1280;

  let langTick = $state(0); // bump on language switch → re-localize labels
  const t = (key: string, fallback: string): string => {
    void langTick;
    try {
      const v = translate(key);
      if (v && v !== key) return v;
    } catch {
      /* non-fatal */
    }
    return fallback;
  };

  let open = $state(false);
  let capturing = $state(false);
  let submitting = $state(false);

  // The current (possibly annotated) screenshot lives on the canvas; this is
  // just the pristine base image used by "Clear"/"Retake".
  let baseImageDataUrl = $state<string | null>(null);
  let hasScreenshot = $state(false);
  let canvasEl = $state<HTMLCanvasElement | undefined>(undefined);
  let tool = $state<"pen" | "rect">("pen");
  let history = $state<string[]>([]);

  let attachments = $state<string[]>([]);
  let description = $state("");

  let drawing = false;
  let dragStart: { x: number; y: number } | null = null;
  let dragSnapshot: ImageData | null = null;

  function openPanel() {
    open = true;
  }

  function resetState() {
    open = false;
    baseImageDataUrl = null;
    hasScreenshot = false;
    history = [];
    attachments = [];
    description = "";
    tool = "pen";
  }

  // --- Screenshot capture ---------------------------------------------------

  function downscaleDataUrl(dataUrl: string, maxWidth: number, quality = 0.85): Promise<string> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        const scale = Math.min(1, maxWidth / img.width);
        const w = Math.max(1, Math.round(img.width * scale));
        const h = Math.max(1, Math.round(img.height * scale));
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) return reject(new Error("no 2d context"));
        ctx.drawImage(img, 0, 0, w, h);
        resolve(canvas.toDataURL("image/jpeg", quality));
      };
      img.onerror = () => reject(new Error("image load failed"));
      img.src = dataUrl;
    });
  }

  function drawBaseImage(): Promise<void> {
    return new Promise((resolve) => {
      if (!canvasEl || !baseImageDataUrl) return resolve();
      const ctx = canvasEl.getContext("2d");
      if (!ctx) return resolve();
      const img = new Image();
      img.onload = () => {
        if (!canvasEl) return resolve();
        canvasEl.width = img.width;
        canvasEl.height = img.height;
        ctx.drawImage(img, 0, 0);
        resolve();
      };
      img.src = baseImageDataUrl;
    });
  }

  async function captureScreenshot() {
    capturing = true;
    // Let Svelte hide the FAB/panel ({#if !capturing}) before the DOM snapshot,
    // then wait one more paint so the hidden widget never appears in the shot.
    await tick();
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    try {
      const rendered = await html2canvas(document.body, {
        useCORS: true,
        scale: Math.min(window.devicePixelRatio || 1, 2),
      });
      const raw = rendered.toDataURL("image/png");
      baseImageDataUrl = await downscaleDataUrl(raw, SCREENSHOT_MAX_WIDTH);
      hasScreenshot = true;
      history = [];
      await tick();
      await drawBaseImage();
    } catch {
      showToast(
        t("bug_report.capture_error", "Could not capture a screenshot — you can still submit without one."),
        "error",
      );
    } finally {
      capturing = false;
    }
  }

  function retake() {
    baseImageDataUrl = null;
    hasScreenshot = false;
    history = [];
  }

  // --- Annotation canvas ------------------------------------------------

  function toCanvasCoords(e: PointerEvent): { x: number; y: number } {
    const rect = canvasEl!.getBoundingClientRect();
    const scaleX = canvasEl!.width / rect.width;
    const scaleY = canvasEl!.height / rect.height;
    return { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY };
  }

  function onPointerDown(e: PointerEvent) {
    if (!canvasEl) return;
    const ctx = canvasEl.getContext("2d");
    if (!ctx) return;
    canvasEl.setPointerCapture?.(e.pointerId);
    history.push(canvasEl.toDataURL());
    const { x, y } = toCanvasCoords(e);
    drawing = true;
    if (tool === "pen") {
      ctx.strokeStyle = "#ef4444";
      ctx.lineWidth = 4;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(x, y);
    } else {
      dragStart = { x, y };
      dragSnapshot = ctx.getImageData(0, 0, canvasEl.width, canvasEl.height);
    }
  }

  function onPointerMove(e: PointerEvent) {
    if (!drawing || !canvasEl) return;
    const ctx = canvasEl.getContext("2d");
    if (!ctx) return;
    const { x, y } = toCanvasCoords(e);
    if (tool === "pen") {
      ctx.lineTo(x, y);
      ctx.stroke();
    } else if (dragStart && dragSnapshot) {
      ctx.putImageData(dragSnapshot, 0, 0);
      ctx.strokeStyle = "#ef4444";
      ctx.lineWidth = 4;
      ctx.strokeRect(dragStart.x, dragStart.y, x - dragStart.x, y - dragStart.y);
    }
  }

  function onPointerUp() {
    drawing = false;
    dragStart = null;
    dragSnapshot = null;
  }

  function undo() {
    if (!canvasEl) return;
    const last = history.pop();
    if (!last) return;
    const ctx = canvasEl.getContext("2d");
    if (!ctx) return;
    const img = new Image();
    img.onload = () => ctx.drawImage(img, 0, 0);
    img.src = last;
  }

  async function clearAnnotations() {
    history = [];
    await drawBaseImage();
  }

  // --- Attachments ---------------------------------------------------------

  function fileToDataUrl(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = () => reject(new Error("file read failed"));
      reader.readAsDataURL(file);
    });
  }

  async function onFilesSelected(e: Event) {
    const input = e.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    input.value = "";
    if (!files.length) return;
    const room = MAX_ATTACHMENTS - attachments.length;
    if (files.length > room) {
      showToast(
        t("bug_report.too_many_attachments", `You can attach up to ${MAX_ATTACHMENTS} images.`),
        "error",
      );
    }
    for (const file of files.slice(0, Math.max(room, 0))) {
      try {
        const raw = await fileToDataUrl(file);
        const small = await downscaleDataUrl(raw, ATTACHMENT_MAX_WIDTH, 0.8);
        attachments.push(small);
      } catch {
        /* skip unreadable file */
      }
    }
  }

  function removeAttachment(index: number) {
    attachments.splice(index, 1);
  }

  // --- Submit ----------------------------------------------------------------

  async function submit() {
    const trimmed = description.trim();
    if (!trimmed) {
      showToast(t("bug_report.description_required", "Please describe the bug."), "error");
      return;
    }
    submitting = true;
    try {
      const finalScreenshot = hasScreenshot && canvasEl ? canvasEl.toDataURL("image/jpeg", 0.85) : undefined;
      await createBugReport({
        description: trimmed,
        page_url: window.location.href,
        user_agent: navigator.userAgent,
        screenshot: finalScreenshot,
        attachments: attachments.length ? attachments : undefined,
      });
      showToast(t("bug_report.submitted", "Thanks — your report was submitted."), "success");
      resetState();
    } catch (err) {
      showToast(
        err instanceof Error ? err.message : t("bug_report.submit_error", "Could not submit the report."),
        "error",
      );
    } finally {
      submitting = false;
    }
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape" && open && !submitting) {
      open = false;
    }
  }

  onMount(() => {
    document.querySelectorAll<HTMLElement>("[data-bug-report-open]").forEach((el) => {
      el.addEventListener("click", openPanel);
    });
    const onLang = () => (langTick += 1);
    window.addEventListener("languageChanged", onLang);
    document.addEventListener("keydown", onKeydown);
    return () => {
      window.removeEventListener("languageChanged", onLang);
      document.removeEventListener("keydown", onKeydown);
    };
  });
</script>

{#if !capturing}
  <div class="fixed bottom-4 right-4 z-[9999] flex flex-col items-end gap-3">
    {#if open}
      <div
        class="flex max-h-[80vh] w-[360px] max-w-[calc(100vw-2rem)] flex-col overflow-y-auto rounded-2xl border border-gray-200 bg-white p-4 shadow-2xl dark:border-gray-800 dark:bg-gray-900"
        role="dialog"
        aria-label={t("bug_report.panel_title", "Report a bug")}
      >
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-sm font-bold text-gray-900 dark:text-white">
            {t("bug_report.panel_title", "Report a bug")}
          </h3>
          <button
            type="button"
            class="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
            onclick={() => (open = false)}
            aria-label={t("common.close", "Close")}
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>

        {#if !hasScreenshot}
          <button
            type="button"
            class="mb-4 inline-flex items-center justify-center gap-2 rounded-lg border border-dashed border-gray-300 px-3 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
            onclick={captureScreenshot}
          >
            {t("bug_report.capture_cta", "Capture a screenshot")}
          </button>
        {:else}
          <div class="mb-2 flex items-center justify-between gap-2">
            <div class="inline-flex items-center gap-1 rounded-lg border border-gray-200 p-1 dark:border-gray-700">
              <button
                type="button"
                class:selected={tool === "pen"}
                class="tool-btn"
                onclick={() => (tool = "pen")}
                aria-pressed={tool === "pen"}
                title={t("bug_report.tool_pen", "Draw")}
              >
                ✏️
              </button>
              <button
                type="button"
                class:selected={tool === "rect"}
                class="tool-btn"
                onclick={() => (tool = "rect")}
                aria-pressed={tool === "rect"}
                title={t("bug_report.tool_rect", "Rectangle")}
              >
                ▭
              </button>
            </div>
            <div class="flex items-center gap-1">
              <button
                type="button"
                class="rounded-md px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-40 dark:text-gray-300 dark:hover:bg-gray-800"
                onclick={undo}
                disabled={history.length === 0}
              >
                {t("bug_report.undo", "Undo")}
              </button>
              <button
                type="button"
                class="rounded-md px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                onclick={clearAnnotations}
              >
                {t("bug_report.clear", "Clear")}
              </button>
              <button
                type="button"
                class="rounded-md px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                onclick={retake}
              >
                {t("bug_report.retake", "Retake")}
              </button>
            </div>
          </div>
          <canvas
            bind:this={canvasEl}
            class="mb-4 w-full touch-none rounded-lg border border-gray-200 dark:border-gray-700"
            onpointerdown={onPointerDown}
            onpointermove={onPointerMove}
            onpointerup={onPointerUp}
            onpointerleave={onPointerUp}
          ></canvas>
        {/if}

        <div class="mb-4">
          <label class="mb-1 block text-xs font-semibold text-gray-600 dark:text-gray-400" for="bug-report-attach">
            {t("bug_report.attach_images", "Attach images")} ({attachments.length}/{MAX_ATTACHMENTS})
          </label>
          {#if attachments.length > 0}
            <div class="mb-2 flex flex-wrap gap-2">
              {#each attachments as src, i}
                <div class="relative h-14 w-14 overflow-hidden rounded-md border border-gray-200 dark:border-gray-700">
                  <img {src} alt="" class="h-full w-full object-cover" />
                  <button
                    type="button"
                    class="absolute right-0 top-0 flex h-5 w-5 items-center justify-center rounded-bl-md bg-black/60 text-xs text-white"
                    onclick={() => removeAttachment(i)}
                    aria-label={t("bug_report.remove_attachment", "Remove")}
                  >
                    ✕
                  </button>
                </div>
              {/each}
            </div>
          {/if}
          {#if attachments.length < MAX_ATTACHMENTS}
            <input
              id="bug-report-attach"
              type="file"
              accept="image/*"
              multiple
              class="block w-full text-xs text-gray-500 dark:text-gray-400"
              onchange={onFilesSelected}
            />
          {/if}
        </div>

        <div class="mb-4">
          <label class="mb-1 block text-xs font-semibold text-gray-600 dark:text-gray-400" for="bug-report-description">
            {t("bug_report.description_label", "What went wrong?")}
          </label>
          <textarea
            id="bug-report-description"
            bind:value={description}
            rows="3"
            placeholder={t("bug_report.description_placeholder", "Describe the bug — what did you expect, what happened instead?")}
            class="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-inner focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100 focus:outline-none dark:border-gray-800 dark:bg-gray-950 dark:text-white/90"
          ></textarea>
        </div>

        <div class="flex items-center justify-end gap-2">
          <button
            type="button"
            class="rounded-lg px-3 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-white/5"
            onclick={() => (open = false)}
            disabled={submitting}
          >
            {t("bug_report.cancel", "Cancel")}
          </button>
          <button
            type="button"
            class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60 dark:bg-indigo-500 dark:hover:bg-indigo-400"
            onclick={submit}
            disabled={submitting}
          >
            {submitting ? t("bug_report.submitting", "Submitting…") : t("bug_report.submit", "Submit")}
          </button>
        </div>
      </div>
    {/if}

    <button
      type="button"
      class="flex h-14 w-14 items-center justify-center rounded-full bg-amber-500 text-2xl text-white shadow-lg transition hover:bg-amber-600"
      onclick={openPanel}
      title={t("bug_report.fab_title", "Report a bug")}
      aria-label={t("bug_report.fab_title", "Report a bug")}
    >
      🐞
    </button>
  </div>
{/if}

<style>
  .tool-btn {
    display: inline-flex;
    height: 1.75rem;
    width: 1.75rem;
    align-items: center;
    justify-content: center;
    border-radius: 0.375rem;
    font-size: 0.875rem;
  }
  .tool-btn.selected {
    background-color: rgb(238 242 255);
  }
  :global(.dark) .tool-btn.selected {
    background-color: rgba(99, 102, 241, 0.15);
  }
</style>
