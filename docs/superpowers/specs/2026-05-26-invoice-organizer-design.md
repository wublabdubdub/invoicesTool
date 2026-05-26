# Invoice Organizer Design

## Goal

Replace the existing reimbursement-sheet/export workflow with a folder organizer that copies imported invoice files into category folders using the current recognized invoice data.

## Approved Behavior

- Remove the "生成报销单" workflow, including Excel reimbursement sheet export and ZIP reimbursement package export.
- Add a "整理发票" action in the top bar.
- When clicked, the user chooses a parent directory.
- The app creates a fixed `整理发票` child directory under that parent.
- Each run deletes only the existing `整理发票` child directory, then rebuilds it from current invoice records.
- The organizer groups files by the invoice `category` currently stored in the database.
- Main invoice files are copied from the app-managed stored original path, `invoices.file_path`.
- Main invoice filenames use recognized vendor plus amount: `商家_金额元.ext`.
- When a vendor is missing, use `未知商家`; when amount is missing, use `未知金额`.
- Keep the original file extension for PDF and image invoices.
- If filenames collide in the same category folder, append `_2`, `_3`, and so on.
- Bound trip-itinerary attachments follow their parent invoice into the same category folder and use `商家_金额元_行程单_N.ext`.
- Missing source files are skipped and counted instead of aborting the whole run.

## Architecture

The feature is implemented in the Electron main process because it needs directory selection, controlled folder deletion, and file copying. A new organizer handler queries invoice rows and attachments from sql.js, sanitizes Windows-safe folder and file names, deletes and recreates the fixed output folder, then copies files. The renderer exposes a single top-bar button that calls the preload API and displays a short result summary.

## Safety Rules

- The user-selected directory is treated as a parent directory only.
- The app deletes only `path.resolve(parent, '整理发票')`.
- Before deletion, the handler verifies the target directory is exactly the fixed child directory of the selected parent.
- File and folder names strip invalid Windows characters, control characters, trailing spaces/dots, and reserved Windows device names.

## Out of Scope

- No database schema change.
- No attempt to copy the user's original pre-import source path, because that path is not stored.
- No Excel or ZIP export remains after this change.
