# Image Invoice Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support `jpg`, `jpeg`, and `png` invoice files with the same user workflow as existing PDF invoices.

**Architecture:** Treat PDF and supported image formats as invoice documents that share the same database record shape and import pipeline. Preserve original extensions on disk, branch OCR and preview behavior by extension, and keep Excel export unchanged while ZIP export preserves each file type.

**Tech Stack:** Electron 33, React 18, TypeScript, sql.js, Python OCR script with PaddleOCR, PyMuPDF, OpenCV.

---

### Task 1: Import And IPC

**Files:**
- Modify: `src/main/handlers/fileHandler.ts`
- Modify: `src/main/index.ts`
- Modify: `src/preload/index.ts`

- [x] Replace PDF-only extension checks with `pdf`, `jpg`, `jpeg`, and `png`.
- [x] Preserve source file extensions when copying invoices and attachments.
- [x] Keep existing IPC names for compatibility, but update filters and types to refer to invoice files.

### Task 2: OCR And Folder Scan

**Files:**
- Modify: `scripts/ocr.py`

- [x] Add helpers to detect PDF versus supported image files.
- [x] Decode images with OpenCV using Unicode-safe file reads.
- [x] Run QR detection directly on images.
- [x] Run OCR directly on images.
- [x] Include images in recursive folder scan and classify them as invoice, trip itinerary, or other.

### Task 3: Preview And Export

**Files:**
- Modify: `src/main/handlers/fileHandler.ts`
- Modify: `src/main/handlers/exportHandler.ts`
- Modify: `src/renderer/src/components/PdfPreview.tsx`

- [x] Return file data with MIME type instead of assuming every preview is a PDF.
- [x] Render PDF invoices through `react-pdf` and image invoices through `<img>`.
- [x] Preserve original extensions in ZIP invoice and attachment names.

### Task 4: Docs And Verification

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `AGENTS_PROJECT.md`
- Modify: `AGENTS_STATUS.md`
- Modify: `AGENTS_TODO.md`

- [x] Document image invoice support.
- [x] Record implementation status in all four handoff files.
- [x] Run `npm run build`.
- [x] Run targeted OCR smoke checks against the test invoice directory when Python dependencies are available.
