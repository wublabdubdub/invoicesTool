# Agent Project Context

## Project Overview

This is an Electron desktop app for organizing invoice PDFs and image invoices for reimbursement-preparation workflows.
It supports local PDF / `jpg` / `jpeg` / `png` import, duplicate detection, OCR-assisted invoice parsing, manual correction, filtering, and folder-based invoice organization.

## Core Workflows

- Import one or more invoice PDFs or image files.
- Scan folders for PDF, JPG, JPEG, and PNG files before import.
- Deduplicate files by MD5 hash.
- Run OCR/parsing and backfill invoice fields.
- Identify taxi itinerary documents and attach them to taxi invoices.
- Manually edit invoice metadata such as date, amount, category, project, and notes.
- Filter invoice records by keyword, category, project, and date.
- Organize imported invoice originals into a regenerated `整理发票` folder under a user-selected parent directory.
- Copy bound taxi itinerary attachments into the same category folder as their parent invoice.

## Tech Stack

- Electron 33
- React 18
- TypeScript
- Vite / electron-vite
- Tailwind CSS
- Zustand
- sql.js
- Python OCR script using PaddleOCR and PyMuPDF

## Important Files

- `src/main/index.ts` - Electron main process entry point and IPC registration.
- `src/main/handlers/dbHandler.ts` - local SQLite/sql.js persistence.
- `src/main/handlers/fileHandler.ts` - file import, scanning, attachment, and file deletion operations.
- `src/main/handlers/organizeHandler.ts` - folder-based invoice organization behavior.
- `src/main/handlers/ocrHandler.ts` - bridge between Electron and Python OCR.
- `src/preload/index.ts` - preload API exposed to the renderer.
- `src/renderer/src/App.tsx` - renderer app root and main layout.
- `src/renderer/src/stores/invoiceStore.ts` - invoice state and renderer-side actions.
- `src/renderer/src/types/invoice.ts` - shared renderer invoice types.
- `src/renderer/src/components/` - UI components for import, list, filters, editing, organizing, and settings.
- `scripts/ocr.py` - OCR/parsing script packaged as an extra resource.

## Data Storage

Application data is stored in Electron `userData`:

- Database: `<userData>/data/invoices.sqlite`
- Invoice files: `<userData>/invoices/*.{pdf,jpg,jpeg,png}`
- Taxi itinerary attachment files: `<userData>/attachments/*.{pdf,jpg,jpeg,png}`

## Test Data

All test invoices for this project come from:

```text
C:\四维纵横\gitee\invoicesTool\20260506深圳
```

Use this directory when validating invoice import, OCR parsing, taxi itinerary matching, filtering, and organizer behavior.
Image invoice support covers `jpg`, `jpeg`, and `png` image files.
Implementation preserves each imported file's original extension in stored paths and organized folder output.

## Organizer Notes

- The `整理发票` action asks the user to select a parent directory.
- The app deletes and recreates only the fixed child directory `<selected parent>/整理发票`.
- The safety check in `organizeHandler.ts` verifies the delete target is exactly that fixed child directory.
- Main invoice files are copied from stored originals at `invoices.file_path`; the original pre-import source path is not stored.
- Category folders are based on the current database value, so manual corrections are reflected.
- Main files are named `vendor_amount.ext`, with `未知商家` and `未知金额` fallbacks.
- Same-name conflicts in a category folder receive `_2`, `_3`, etc.
- Bound trip-itinerary attachments are copied into the same category folder and named with `_行程单_N`.
- Missing invoice or attachment source files are skipped and counted instead of aborting the full run.

## OCR Notes

- PDF files use QR parsing, embedded text extraction, and OCR fallback.
- Image files use QR parsing and OCR.
- The OCR server starts lazily so QR-only results can still be returned when the PaddleOCR model fails to initialize.
- Automatic import starts with fast mode (`deep_ocr=false`): text-based PDFs are parsed from embedded text; QR-readable images/non-text files return QR fields without PaddleOCR; non-text/no-QR files return `_source = "ocr_skipped"` and are then retried once with deep OCR so scanned invoices such as aviation itineraries can still be backfilled during import.
- Manual re-recognition and taxi itinerary matching use deep mode (`deep_ocr=true`) and may run full PaddleOCR.
- Electron's per-invoice OCR timeout now restarts the Python worker so a timed-out deep OCR request does not keep blocking later requests.

## Development Commands

Use the exact local startup command in `AGENTS_STATUS.md` on this machine.

Common package scripts:

```powershell
npm run dev
npm run build
npm run dist:mac
npm run dist:win
```

On this Windows machine, prefer `npm.cmd` from the Node.js install path documented in `AGENTS_STATUS.md`.

## Implementation Notes

- The app is a local-first desktop tool. Avoid adding network dependencies unless the user explicitly asks.
- OCR can fail if Python dependencies or the configured Python path are missing. Keep import behavior useful even when OCR fails.
- OCR parsing recognizes aviation electronic ticket itinerary invoices as `invoice_type = 行程单` and `category = 城市间交通`.
- Fast folder scanning keeps PDF classification sequential. Threaded calls into PyMuPDF/OpenCV QR extraction can crash the Python process on Windows with access violation code `3221225477`.
- QR-readable image invoices use a fast seller-region OCR path before full-page OCR.
- Batch import uses a fast foreground pass plus a main-process background OCR queue.
- Manual re-recognition, background `ocr_skipped` completion, and taxi itinerary attachment OCR use a 180s timeout because local PaddleOCR can take around 70s for the aviation scanned-PDF sample.
- OCR classification rule: when the recognized seller/vendor starts with `上海蒜芽科技` or `上海蒜芽信息科技`, classify the invoice as `城市间交通` while leaving invoice type and monetary fields to existing parsing logic.
- Taxi itinerary documents are attachments, not independent reimbursement amounts.
- Organizer behavior is user-facing and should be verified carefully after file, itinerary, category, or naming changes.
- Packaging includes the `scripts` directory through `build.extraResources` in `package.json`.

## Agent Handoff Policy

All future planning and development work must update the four agent handoff files listed in `AGENTS.md`.
This policy is about agent continuity only; it does not change application architecture or runtime behavior.

## Recent Handoff Notes

- 2026-05-26: Default desktop layout now starts with a wider 448px filter/sidebar and the top-left import buttons align to the toolbar's left padding instead of after the old window-control spacer.
- 2026-05-26: The main Electron window now removes the default native menu bar (`File/Edit/View/Window/Help`) while preserving the app's own toolbar.
- 2026-05-26: Aviation itinerary OCR seller extraction now handles OCR output such as `开单位：深圳航空有限责任公司` and rejects table headers like `航班号` as vendor values.
- 2026-05-26: Removed Excel/ZIP reimbursement export and added the regenerated category-folder `整理发票` workflow. `npm run build` passed.
- 2026-05-25: Batch import no longer waits on the slow image seller-crop OCR or scanned-PDF deep OCR paths; those run in the background and surface as per-invoice loading state.
- 2026-05-25: Image invoice merchant recognition improved with seller-region crop OCR; the 达美乐 sample now fills vendor in about 20s instead of full-page OCR at about 128s.
- 2026-05-25: Fixed aviation itinerary recognition by retrying `ocr_skipped` imports with deep OCR, lowering deep-OCR render scale, extending deep OCR timeout, and making aviation fare-table parsing tolerant of low-scale OCR errors; also expanded the Shanghai Suanya rule to `上海蒜芽信息科技`.
- 2026-05-25: Folder batch-import scan crash fixed by removing threaded PDF fast-scan classification; test directory fast scan and `npm run build` passed.
- 2026-05-25: Import OCR speedup implemented; automatic import is fast and conservative, while manual re-recognition remains the path for full scanned-document OCR.
- 2026-05-25: Image invoice support is implemented without a database schema change.
