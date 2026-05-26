# OCR Import Speedup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make batch import recognition return quickly for QR/text-readable invoices while preserving deep OCR for manual re-recognition and true scanned invoices.

**Architecture:** Keep one Python OCR server, but add a request-level fast mode. Import calls use fast mode; manual `run-ocr` calls use deep mode. Fast mode skips PaddleOCR for non-text documents during automatic import; QR-readable images still get QR fields, and scanned/no-QR files are quickly imported with sparse fields for later manual deep recognition.

**Tech Stack:** Electron main process, TypeScript IPC/OCR handler, Python OCR script with PaddleOCR/PyMuPDF/OpenCV.

---

### Task 1: Python Fast Mode

**Files:**
- Modify: `scripts/ocr.py`

- [ ] Add `is_qr_confident(fields)` helper returning true when `invoice_no` exists and either `total` or `date` exists.
- [ ] Change `process(file_path)` to `process(file_path, deep_ocr=False)`.
- [ ] After QR and PDF text extraction, if there is no embedded text and `deep_ocr` is false, return `extract_fields([])` merged with QR fields, `_source = "qr_fast"` when QR is confident or `_source = "ocr_skipped"` when it is not, and empty `_ocr_lines`.
- [ ] Keep current full OCR behavior when `deep_ocr` is true.
- [ ] In server mode, read `deep_ocr = bool(req.get("deep_ocr"))` and pass it to `process()`.

### Task 2: Electron Request Options

**Files:**
- Modify: `src/main/handlers/ocrHandler.ts`
- Modify: `src/main/index.ts`

- [ ] Add `RunOcrOptions = { deepOcr?: boolean; timeoutMs?: number }`.
- [ ] Change `runOcr(filePath)` to `runOcr(filePath, options)`.
- [ ] Send `{ id, path: filePath, deep_ocr: Boolean(options.deepOcr) }` to the Python server.
- [ ] In `autoOcrImportedItems()`, call `runOcr(item.filePath, { deepOcr: false })`.
- [ ] In taxi itinerary attachment OCR and manual IPC `run-ocr`, call `runOcr(..., { deepOcr: true })` so matching/manual re-recognition keeps full OCR.

### Task 3: Timeout Recovery

**Files:**
- Modify: `src/main/handlers/ocrHandler.ts`

- [ ] On per-request timeout, delete the resolver and call `stopOcrProcess()` so the stuck Python process does not keep blocking queued requests.
- [ ] Make `stopOcrProcess()` resolve all still-pending requests as failed before clearing the map, except the timed-out request that was already resolved.

### Task 4: Verification

**Files:**
- Modify: `AGENTS.md`
- Modify: `AGENTS_STATUS.md`
- Modify: `AGENTS_PROJECT.md`
- Modify: `AGENTS_TODO.md`

- [ ] Run `python -m py_compile scripts\ocr.py`.
- [ ] Run a direct fast-mode server or module check showing the two JPG files return QR fast results without `_source` containing `ocr`.
- [ ] Run direct deep OCR on `cd5a30f5bcdcc537e72774ca54311e0c.pdf` to confirm aviation itinerary parsing still works.
- [ ] Run `npm run build`.
- [ ] Run `git diff --check`.
- [ ] Update all four handoff files with the implementation and verification results.
