# Invoice Organizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace reimbursement export with a folder-based invoice organizer.

**Architecture:** Remove the Excel/ZIP export chain and add a focused `organizeHandler` in the Electron main process. The renderer exposes a top-bar "整理发票" button that calls preload IPC and reports copied/skipped counts.

**Tech Stack:** Electron IPC, React, TypeScript, sql.js, Node `fs`/`path`.

---

### Task 1: Remove Reimbursement Export

**Files:**
- Delete: `src/renderer/src/components/ReportModal.tsx`
- Delete: `src/main/handlers/exportHandler.ts`
- Modify: `src/renderer/src/components/TopBar.tsx`
- Modify: `src/preload/index.ts`
- Modify: `src/main/index.ts`
- Modify: `src/renderer/src/components/SettingsModal.tsx`
- Modify: `src/renderer/src/stores/invoiceStore.ts`
- Modify: `src/renderer/src/types/invoice.ts`
- Modify: `package.json`
- Modify: `package-lock.json`

- [ ] Remove `ReportModal` imports, state, button, and render call.
- [ ] Remove `export-report` and `export-zip` preload APIs and main IPC handlers.
- [ ] Remove reimbursement-only settings fields.
- [ ] Remove Excel/ZIP dependencies.

### Task 2: Add Organizer Handler

**Files:**
- Create: `src/main/handlers/organizeHandler.ts`
- Modify: `src/main/index.ts`
- Modify: `src/preload/index.ts`

- [ ] Query invoices and attachments from the database.
- [ ] Ask the user for a parent directory.
- [ ] Safely delete and recreate `<parent>/整理发票`.
- [ ] Copy existing stored invoice files by category and vendor/amount filename.
- [ ] Copy attached trip itineraries beside their parent invoice.
- [ ] Return copied, attachmentCopied, skipped, and output path counts.

### Task 3: Add Top-Bar Action

**Files:**
- Modify: `src/renderer/src/components/TopBar.tsx`

- [ ] Add "整理发票" button where "生成报销单" used to be.
- [ ] Disable while the organizer is running.
- [ ] Alert success, cancel, and failure states.

### Task 4: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `AGENTS_STATUS.md`
- Modify: `AGENTS_PROJECT.md`
- Modify: `AGENTS_TODO.md`

- [ ] Update README to describe folder organizing rather than reimbursement export.
- [ ] Update handoff files with implementation and verification status.
- [ ] Run `npm run build`.
- [ ] Run `git diff --check`.
