# Agent Handoff Guide

Start here when working in this repository.

## Read Order

1. `AGENTS_STATUS.md` - current local environment, branch/remotes, startup notes, known pitfalls.
2. `AGENTS_PROJECT.md` - project purpose, stack, architecture, and important files.
3. `AGENTS_TODO.md` - active and backlog tasks for future agents.
4. `README.md` - user-facing project overview and normal setup instructions.

## Operating Rules

- Work inside this repository unless the user explicitly says otherwise.
- Treat uncommitted changes as user-owned. Do not revert or clean them without permission.
- Do not use destructive git commands such as `git reset --hard` or `git checkout --` unless explicitly requested.
- Do not push to `upstream`. Push development work only to `origin` if the user asks for a push.
- Keep changes focused and consistent with the existing Electron + React + TypeScript patterns.
- For UI work, preserve the dense desktop-tool layout style already used by the app.
- Every time an agent makes a plan or performs development work, the agent must update all four agent handoff files before finishing.

## Startup Command

Use this exact PowerShell command from the repository root to start the development app on this machine:

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

## Standard Verification

Before finalizing code changes, run the build command from `AGENTS_STATUS.md`.
For documentation-only changes, a careful Markdown review and `git diff --check` are usually enough.
All test invoices for this project come from `C:\四维纵横\gitee\invoicesTool\20260506深圳`; use that directory when testing invoice import, OCR, itinerary matching, filtering, and organizer behavior.
Image invoice import/OCR supports `jpg`, `jpeg`, and `png` files with behavior matching existing PDF invoices.
Image invoice support is implemented end-to-end across file selection, folder scan, import storage, OCR, preview, organizer output, README, and these handoff files without changing the database schema.

## Required Handoff Updates

Every planning or development task must update all four handoff files. Do not finish a task with planning, code, documentation, dependency, setup, or behavior changes until these files have been updated:

- `AGENTS.md` - update when agent operating rules, handoff conventions, required checks, or collaboration rules change.
- `AGENTS_STATUS.md` - update when local setup, branch/remotes, verification status, known issues, startup commands, or environment assumptions change.
- `AGENTS_PROJECT.md` - update when architecture, important files, data flow, commands, dependencies, packaging, or project behavior changes.
- `AGENTS_TODO.md` - update when a plan is created, a task starts, a task finishes, something is blocked, or follow-up work is discovered.

If a file has no substantive project change to record, still update it with a concise handoff note, timestamped status entry, or task-board movement that explains why no project-specific content changed.

Before every final response after planning or development, run this checklist:

- [ ] Did I make or change a plan? If yes, record the active or next steps in `AGENTS_TODO.md`.
- [ ] Did I change code, docs, dependencies, scripts, setup, or user-visible behavior? If yes, update the relevant agent files.
- [ ] Did verification pass, fail, or get skipped? If relevant, record the result in `AGENTS_STATUS.md` or `AGENTS_TODO.md`.
- [ ] Did I learn or change stable project context? If yes, update `AGENTS_PROJECT.md`.
- [ ] Did I change agent rules or handoff expectations? If yes, update `AGENTS.md`.

## Handoff Notes

- 2026-05-26: Adjusted the default filter/sidebar width to match the requested screenshot and moved the top-left import buttons flush to the app toolbar's left padding; no agent operating rules changed.
- 2026-05-26: Removed the default Electron window menu bar (`File/Edit/View/Window/Help`) from the main app window; no agent operating rules changed.
- 2026-05-26: Fixed aviation itinerary OCR vendor extraction so `开单位：深圳航空有限责任公司` is preferred and table headers such as `航班号` are rejected as seller names; no agent operating rules changed.
- 2026-05-26: Removed the reimbursement-sheet/export workflow and added a regenerated category-folder `整理发票` workflow; `npm run build` and `git diff --check` passed; no agent operating rules changed.
- 2026-05-25: Changed batch import OCR to fast foreground plus background slow recognition with UI loading status; no agent operating rules changed.
- 2026-05-25: Added image-invoice seller-region OCR fast path so QR-readable JPG/PNG invoices can fill merchant names without full-page OCR; no agent operating rules changed.
- 2026-05-25: Fixed aviation itinerary auto/manual OCR timeout/low-scale parsing and `上海蒜芽信息科技` classification; no agent operating rules changed.
- 2026-05-25: Fixed folder batch-import scan crash by keeping fast PDF scan classification sequential; no agent operating rules changed.
- 2026-05-25: Implemented import OCR speedup: automatic imports now use fast OCR mode, manual re-recognition uses deep OCR, and timed-out OCR requests restart the Python worker.
- 2026-05-25: Diagnosed slow import recognition; root cause is sequential OCR plus unnecessary full PaddleOCR for QR-confident image files and non-cancelled Python OCR work after Electron request timeout.
- 2026-05-25: Copied the verified local startup command into this file for quicker agent onboarding.
- 2026-05-25: Image invoice support was implemented and the dev server was started successfully at `http://localhost:5173/`; no agent operating rules changed.
- 2026-05-25: Final verification for the `上海蒜芽科技` classification rule completed; no agent operating rules changed.
- 2026-05-25: Implemented focused OCR classification rule for invoices whose vendor starts with `上海蒜芽科技`; no agent operating rules changed.
- 2026-05-25: Added aviation electronic ticket itinerary invoice parsing; no agent operating rules changed.
- 2026-05-25: Planned a focused OCR classification rule for invoices whose vendor starts with `上海蒜芽科技`; no agent operating rules changed.
