# Agent TODO Board

This file tracks actionable work for future agents.
Move items between sections as work starts and finishes.

## Active

No active task is currently assigned.

## Next

- [ ] Consider process-based OCR parallelism for heavy OCR files only, using 1-2 worker processes and keeping PyMuPDF/OpenCV QR/text scan calls out of Python threads.
- [ ] Add timing logs around `autoOcrImportedItems()` and `scripts/ocr.py process()` so slow files are visible in future runs.
- [ ] Review the existing local modification in `scripts/ocr.py` before touching OCR behavior.
- [ ] Decide whether `scripts/__pycache__/` should be deleted locally or added to `.gitignore`.
- [ ] Run the documented dev startup command before UI or Electron workflow changes.
- [ ] Run `npm run build` after code changes.

## Backlog

- [ ] Add focused tests or manual verification notes for OCR parsing edge cases when OCR behavior changes.
- [ ] Add organizer verification notes when changing invoice, itinerary, file-copy, or folder output behavior.
- [ ] Keep README and agent docs aligned when setup or workflow changes.

## Done

- [x] 2026-05-26: Adjusted default filter/sidebar width and top-left toolbar button alignment to match the requested screenshot. Verification passed: `npm run build`; `git diff --check` passed with only existing LF-to-CRLF warnings.
- [x] 2026-05-26: Removed the default Electron window menu bar from the main window. Verification passed: `npm run build`; `git diff --check` passed with only existing LF-to-CRLF warnings.
- [x] 2026-05-26: Fixed aviation itinerary OCR vendor extraction for the Shenzhen Airlines sample that was previously recognized as `航班号`; direct deep OCR sample verification, `python -m py_compile scripts\ocr.py`, `npm run build`, and `git diff --check` passed. Diff check reported only existing LF-to-CRLF warnings.
- [x] 2026-05-26: Removed the reimbursement-sheet/export workflow, including `ReportModal`, `exportHandler`, export IPC APIs, reimbursement settings, Excel/ZIP README text, and direct `exceljs`/`archiver` dependencies.
- [x] 2026-05-26: Added the "整理发票" workflow. It chooses a parent directory, safely deletes and rebuilds the fixed `整理发票` child folder, groups stored invoice originals by current category, names main files as vendor plus amount, keeps original extensions, resolves collisions, and copies bound trip-itinerary attachments beside their parent invoice.
- [x] 2026-05-26: Verification for the organizer change: `npm run build` passed; `git diff --check` passed with only existing LF-to-CRLF warnings.
- [x] Changed batch import to finish after fast QR/PDF-text OCR and queue slow image/scanned OCR in the background.
- [x] Added renderer background OCR status wiring so invoices currently being completed in the background show the existing loading spinner and refresh when finished.
- [x] Verified foreground fast processing of all 41 supported files in `20260506深圳` completes in 5.36s with no single file over 1s; `python -m py_compile scripts\ocr.py` and `npm run build` passed.
- [x] Added image-invoice seller-region OCR fast path so QR-readable JPG/PNG invoices can fill merchant names without full-page OCR.
- [x] Verified the 达美乐 JPG sample returns `深圳达美乐餐饮管理有限公司` from both fast and deep calls in about 20s with `_source = "qr+seller_crop"`.
- [x] Fixed aviation itinerary auto/manual deep OCR by retrying `ocr_skipped` imports with deep OCR, lowering scanned-PDF render scale to `1.0`, OCRing the first page, extending deep OCR calls to 180s, and parsing the standard aviation fare table despite partial OCR label/currency errors.
- [x] Verified `20260506深圳\cd5a30f5bcdcc537e72774ca54311e0c.pdf` now returns invoice no `26448784110004536740`, date `2026-05-25`, vendor `中国南方航空股份有限公司`, amount `1416.97`, tax `123.03`, total `1540.0`, category `城市间交通`, invoice type `行程单` in 70.18s.
- [x] Expanded the Shanghai Suanya classification rule so `上海蒜芽信息科技有限公司` invoices classify as `城市间交通`; verified `26317000001817415206.pdf` and `26317000001817415204.pdf`.
- [x] Ran `python -m py_compile scripts\ocr.py`, `npm run build`, and `git diff --check` for the aviation/Suanya bug fix after adding the import fallback; diff check only reported existing LF-to-CRLF warnings.
- [x] Fixed folder batch-import scan crash by removing threaded fast-mode PDF classification from `scripts/ocr.py`.
- [x] Verified the scan crash fix with Python compile, direct fast scan of all 41 supported files in `20260506深圳`, stdout/stderr separation, and `npm run build`.
- [x] Implemented OCR import fast mode: automatic imports first skip PaddleOCR for non-text files, returning QR fields when available; later bug fix retries sparse `ocr_skipped` results with deep OCR.
- [x] Kept manual "重新识别" and taxi itinerary matching on deep OCR mode.
- [x] Fixed OCR timeout handling so a timed-out request restarts the Python worker instead of blocking the queue.
- [x] Verified OCR speedup with Python compile, 41-file fast-mode timing, aviation deep OCR, and `npm run build`.
- [x] Diagnosed slow import recognition and identified the main bottlenecks in the OCR pipeline.
- [x] Copied the verified local development startup command into `AGENTS.md`.
- [x] Started the dev environment successfully and verified `http://localhost:5173/` returned 200.
- [x] Added shared document extension support in Electron import and IPC.
- [x] Planned and implemented OCR vendor-prefix classification rule for `上海蒜芽科技*` invoices as `城市间交通`; direct parser smoke check, `python -m py_compile scripts\ocr.py`, and `npm run build` passed.
- [x] Taught `scripts/ocr.py` to scan and OCR `jpg`, `jpeg`, and `png` files.
- [x] Updated renderer preview to display both PDF and image invoices.
- [x] Preserved original file extensions in organized file output.
- [x] Updated README and agent handoff docs after image invoice implementation.
- [x] Ran `npm run build`, Python compile check, test-directory fast scan, and JPG OCR smoke check.
- [x] Added aviation electronic ticket itinerary invoice parsing for `cd5a30f5bcdcc537e72774ca54311e0c.pdf` layout; full direct OCR, `python -m py_compile scripts\ocr.py`, `npm run build`, and `git diff --check` passed.
- [x] Documented that all project test invoices come from `C:\四维纵横\gitee\invoicesTool\20260506深圳`.
- [x] Required all future planning and development work to update the four agent handoff files.
- [x] Fork created under `wublabdubdub/invoicesTool`.
- [x] Local repo configured with `origin` as the fork and `upstream` as the original source.
- [x] Node.js installed locally through `winget`.
- [x] Dependencies installed with `npm.cmd install`.
- [x] Electron binary restored and verified.
- [x] Dev startup command verified.
- [x] Added four future-agent handoff files.
