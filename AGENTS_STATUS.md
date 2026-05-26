# Agent Status

This file tracks the current local status for future agents.
For stable project context, read `AGENTS_PROJECT.md`.
For active work items, read `AGENTS_TODO.md`.

## Repository

- Local path: `C:\四维纵横\gitee\invoicesTool`
- Fork origin: `https://github.com/wublabdubdub/invoicesTool.git`
- Upstream source: `https://github.com/OldConcept/invoicesTool.git`
- Current branch: `main`
- Upstream push is intentionally disabled: `upstream DISABLED (push)`

Do not push to `upstream`. Push development work to `origin`.

## Project Overview

See `AGENTS_PROJECT.md`.

## Verified Local Startup

Use this exact PowerShell command from the repo root:

```powershell
cd C:\四维纵横\gitee\invoicesTool
Remove-Item Env:\ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
$nodeDir = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.16.0-win-x64"
$env:Path = "$nodeDir;$env:Path"
& "$nodeDir\npm.cmd" run dev
```

Expected result:

- Vite renderer dev server starts at `http://localhost:5173/`.
- Electron launches the desktop app window.
- Keep the PowerShell window open while developing.

## Environment Notes

- Node.js LTS is installed through `winget` under:
  `C:\Users\z1109\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.16.0-win-x64`
- Use `npm.cmd` in PowerShell to avoid `npm.ps1` execution policy errors.
- `node_modules` is installed.
- `npm run build` has passed once after dependency installation.
- `npm install` reported existing dependency audit warnings. Do not run `npm audit fix --force` without explicit approval.
- Test invoices are located at `C:\四维纵横\gitee\invoicesTool\20260506深圳`.
- The test invoice directory currently scans as 41 supported files: 39 PDF files and 2 JPG files.

## Known Startup Pitfalls

### Electron binary missing

The app previously failed with:

```text
Error: Electron uninstall
```

Cause: `node_modules/electron/dist` was incomplete and did not contain `electron.exe`.

Current status:

- `node_modules/electron/dist/electron.exe` exists.
- `node_modules/electron/path.txt` contains `electron.exe`.

If this happens again, re-download or restore the Electron binary before debugging app code.

### ELECTRON_RUN_AS_NODE

The environment previously had:

```text
ELECTRON_RUN_AS_NODE=1
```

Clear it before starting the dev app:

```powershell
Remove-Item Env:\ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
```

## Current Working Tree Notes

At the time this file was created, the repo already had unrelated local changes:

```text
M  scripts/ocr.py
?? scripts/__pycache__/
```

Treat these as user-owned changes unless the user explicitly asks you to modify or clean them.

## Completed Setup

- [x] Fork created under `wublabdubdub/invoicesTool`.
- [x] Local repo configured with `origin` as the fork and `upstream` as the original source.
- [x] Node.js installed locally through `winget`.
- [x] Dependencies installed with `npm.cmd install`.
- [x] Electron binary restored and verified.
- [x] Dev startup command verified.

## Agent Operating Rules

- See `AGENTS.md`.
- Before finalizing code changes, run at least:

```powershell
$nodeDir = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.16.0-win-x64"
$env:Path = "$nodeDir;$env:Path"
& "$nodeDir\npm.cmd" run build
```

## Update Log

- 2026-05-26: Adjusted renderer layout per screenshot. The filter/sidebar default width is now `448px` with a wider resize range (`320px`-`560px`), and the top-left import button group no longer has the old `w-16` spacer before it. Verification passed: `npm run build`; `git diff --check` passed with only existing LF-to-CRLF warnings.
- 2026-05-26: Removed the default Electron window menu bar (`File/Edit/View/Window/Help`) by setting `autoHideMenuBar: true` and `mainWindow.setMenu(null)` in `src/main/index.ts`. This keeps the native title bar and app toolbar while removing the framed menu row shown in the UI screenshot. Verification passed: `npm run build`; `git diff --check` passed with only existing LF-to-CRLF warnings.
- 2026-05-26: Fixed an aviation electronic ticket itinerary OCR bug where deep OCR could set the seller/vendor to the table header `航班号`. The parser now prefers `填开单位` / OCR-misread `开单位` / `开具单位`, rejects common itinerary table labels as vendor candidates, and only uses `承运人` when it has an explicit same-line value. Direct verification on `C:\Users\z1109\AppData\Roaming\invoices-tool\invoices\5c4ec54f-4dc5-4d9b-b410-e8bef2205aae.pdf` returned vendor `深圳航空有限责任公司`, invoice no `26958479111036679022`, date `2026-05-26`, amount `618.8`, tax `51.2`, total `670.0`, category `城市间交通`, invoice type `行程单`; `python -m py_compile scripts\ocr.py`, `npm run build`, and `git diff --check` passed. Diff check reported only existing LF-to-CRLF warnings.
- 2026-05-26: Replaced the reimbursement-sheet/export workflow with the folder-based "整理发票" workflow. Removed `ReportModal`, `exportHandler`, export IPC/preload APIs, reimbursement settings, README export text, and direct `exceljs`/`archiver` dependencies. Added `src/main/handlers/organizeHandler.ts` plus a top-bar "整理发票" button; the organizer chooses a parent directory, safely deletes/rebuilds only the fixed `整理发票` child folder, groups stored invoice originals by current category, names files from vendor plus amount, resolves same-name collisions, and copies bound trip-itinerary attachments beside their parent invoice. Verification passed: `npm run build`; `git diff --check` passed with only existing LF-to-CRLF warnings.
- 2026-05-25: Changed batch import recognition to a two-stage flow. Foreground import now calls OCR with `deepOcr=false` and `enrichImageSeller=false`, so QR/image seller-crop OCR and scanned-PDF deep OCR no longer block import completion; slow image/scanned items are queued in a main-process background OCR worker and exposed to the renderer through `background-ocr-status` so the list/detail UI can show loading and refresh completed invoices. Verification passed: `python -m py_compile scripts\ocr.py`; foreground fast processing of all 41 supported files in `20260506深圳` completed in 5.36s with no single file over 1s; `npm run build` passed; `git diff --check` reported only existing LF-to-CRLF warnings.
- 2026-05-25: Added a seller-region OCR fast path for QR-readable image invoices. Image invoices now merge QR fields with OCR from likely sales-party crops and return early for both automatic import and manual re-recognition when a merchant is found, avoiding full-page PaddleOCR for this common case. Verification passed: `python -m py_compile scripts\ocr.py`; sample `d203c084-c0f3-47ea-a2c5-c592bf6be409.jpg` returned vendor `深圳达美乐餐饮管理有限公司` with `_source = "qr+seller_crop"` in about 20s for both fast and deep calls instead of the previously measured about 128s full OCR; `npm run build` passed. The crop fast path intentionally does not trust cropped OCR tax IDs because the sample misread `C08D` as `CQ8D`.
- 2026-05-25: Fixed two OCR bugs from the UI screenshots. Aviation electronic ticket itinerary deep OCR now renders PDF pages at scale `1.0`, OCRs only the first page, parses the standard fare table even when currency/labels are partially misrecognized, Electron manual/deep OCR calls use a 180s timeout, and automatic import retries deep OCR when the fast result is `_source = "ocr_skipped"`. Direct verification passed for `20260506深圳\cd5a30f5bcdcc537e72774ca54311e0c.pdf` in 70.18s with invoice no `26448784110004536740`, date `2026-05-25`, vendor `中国南方航空股份有限公司`, amount `1416.97`, tax `123.03`, total `1540.0`, category `城市间交通`, invoice type `行程单`. `上海蒜芽信息科技有限公司` invoices `26317000001817415206.pdf` and `26317000001817415204.pdf` now classify as `城市间交通`. Verification passed: `python -m py_compile scripts\ocr.py`, `npm run build`, and `git diff --check` with only existing LF-to-CRLF warnings.
- 2026-05-25: Fixed `scan-folder` crash during folder batch import. Root cause was fast-mode threaded PDF classification calling PyMuPDF/OpenCV QR extraction from multiple Python threads, which reproduced as a Windows access violation before JSON output. Verification passed: `python -m py_compile scripts\ocr.py`; `python scripts\ocr.py --scan "C:\四维纵横\gitee\invoicesTool\20260506深圳" --mode fast` returned JSON for 41 supported files with exit code 0; stdout redirection confirmed JSON stayed on stdout while OpenCV QR warnings stayed on stderr; `npm run build` passed.
- 2026-05-25: Implemented import OCR speedup. Automatic import calls now use `deep_ocr=false`; non-text documents skip PaddleOCR in import mode (`qr+qr_fast` when QR is reliable, `ocr_skipped` when not), manual `run-ocr` and taxi itinerary matching use `deep_ocr=true`, and per-file OCR timeout restarts the Python worker. Verification passed: `python -m py_compile scripts\ocr.py`; fast-mode processing of all 41 supported files in `20260506深圳` completed in 9.12s with sources `{qr+text:36,text:2,ocr_skipped:1,qr+qr_fast:2}`; deep OCR for `cd5a30f5bcdcc537e72774ca54311e0c.pdf` still returned the expected aviation itinerary fields; `npm run build` passed.
- 2026-05-25: Diagnosed slow import recognition using `20260506深圳`: cheap QR/text profiling found 41 supported files, 38 text-based PDFs, and only 3 current full-OCR candidates (`cd5a30f5bcdcc537e72774ca54311e0c.pdf` plus 2 JPGs). Ten text-based PDFs processed in 1.655s total (~165.5ms each). The slow path is unnecessary full OCR for QR-confident images and sequential Electron OCR with a 30s timeout that does not stop the Python worker.
- 2026-05-25: Copied the verified dev startup command from this file into `AGENTS.md`; no runtime behavior changed.
- 2026-05-25: Dev server started successfully after clearing `ELECTRON_RUN_AS_NODE`; renderer responded at `http://localhost:5173/`.
- 2026-05-25: Implemented OCR vendor-prefix classification rule for `上海蒜芽科技*` invoices as `城市间交通`. Direct `extract_fields()` smoke check passed (`上海蒜芽科技有限公司` -> `城市间交通`, `invoice_type` unchanged as `其他`); `npm run build` and `python -m py_compile scripts\ocr.py` passed; `git diff --check` reported only existing CRLF line-ending warnings.
- 2026-05-25: Implemented image invoice support for `jpg`, `jpeg`, and `png`; `npm run build`, `python -m py_compile scripts\ocr.py`, and fast scan of the test invoice directory passed. Single JPG OCR returned QR-only fields because this local PaddleOCR runtime reports a oneDNN conversion error during model OCR.
- 2026-05-25: Added OCR parser support for aviation electronic ticket itinerary invoices such as `20260506深圳\cd5a30f5bcdcc537e72774ca54311e0c.pdf`; fixed the local PaddleOCR 3.5.0 / Paddle 3.3.1 oneDNN runtime failure by constructing `PaddleOCR` with `enable_mkldnn=False`. Direct sample OCR returned invoice no `26448784110004536740`, date `2026-05-25`, vendor `中国南方航空股份有限公司`, amount `1416.97`, tax `123.03`, total `1540.0`, category `城市间交通`, and invoice type `行程单`. `python -m py_compile scripts\ocr.py`, `npm run build`, and `git diff --check` passed; diff check only reported existing LF-to-CRLF warnings.
- 2026-05-25: `git diff --check` completed for planning/documentation changes; only existing line-ending warnings were reported.
- 2026-05-25: Planning focused OCR classification rule: invoices whose recognized vendor starts with `上海蒜芽科技` should be categorized as `城市间交通`; no verification run yet.
- 2026-05-25: Started implementation plan for end-to-end image invoice support without a database schema change.
- 2026-05-25: Planning image-format invoice support for `jpg`, `jpeg`, and `png` files.
- 2026-05-25: Documented the project test invoice directory in the agent handoff files.
- 2026-05-25: Updated `AGENTS.md` to require all four agent handoff files to be updated after every planning or development task.
- 2026-05-25: Split future-agent handoff into `AGENTS.md`, `AGENTS_PROJECT.md`, `AGENTS_STATUS.md`, and `AGENTS_TODO.md`.
- 2026-05-25: Created this agent handoff/status file after fork setup and dev startup verification.
