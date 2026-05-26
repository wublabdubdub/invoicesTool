# Shanghai Suanya Traffic Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Classify invoices whose recognized vendor starts with `上海蒜芽科技` as `城市间交通`.

**Architecture:** Add a narrow vendor-prefix override in `scripts/ocr.py` after existing category keyword classification. Keep the rule in OCR extraction so existing Electron persistence, filtering, and export behavior continue to work without schema or UI changes.

**Tech Stack:** Python OCR parser (`scripts/ocr.py`), Electron/TypeScript build verification via `npm.cmd run build`.

---

## File Structure

- Modify: `scripts/ocr.py` - add a helper for vendor-prefix matching and apply it before returning OCR fields.
- Modify: `AGENTS.md`, `AGENTS_STATUS.md`, `AGENTS_PROJECT.md`, `AGENTS_TODO.md` - record planning, implementation, and verification status as required by repository handoff rules.
- Create: `docs/superpowers/specs/2026-05-25-shanghai-suanya-traffic-classification-design.md` - approved design.
- Create: `docs/superpowers/plans/2026-05-25-shanghai-suanya-traffic-classification.md` - implementation plan.

### Task 1: Add Vendor Prefix Classification Rule

**Files:**
- Modify: `scripts/ocr.py`

- [x] **Step 1: Add a local helper inside `extract_fields()` near category classification**

```python
    def _vendor_startswith(value, prefix):
        if not value:
            return False
        normalized = re.sub(r'\s+', '', value)
        return normalized.startswith(prefix)
```

- [x] **Step 2: Apply the override after the existing category keyword loop**

```python
    if _vendor_startswith(vendor, '上海蒜芽科技'):
        category = '城市间交通'
```

- [x] **Step 3: Run a direct parser smoke check**

Run:

```powershell
@'
import sys
sys.path.insert(0, 'scripts')
import ocr

data = ocr.extract_fields([
    '购买方名称：测试公司',
    '销售方名称：上海蒜芽科技有限公司',
    '开票日期：2026年05月01日',
    '价税合计（小写）¥123.45',
])
print(data['vendor'])
print(data['category'])
print(data['invoice_type'])
'@ | python -
```

Expected output includes:

```text
上海蒜芽科技有限公司
城市间交通
```

### Task 2: Verify Build And Handoff

**Files:**
- Modify: `AGENTS.md`
- Modify: `AGENTS_STATUS.md`
- Modify: `AGENTS_PROJECT.md`
- Modify: `AGENTS_TODO.md`

- [x] **Step 1: Run the documented build command**

```powershell
$nodeDir = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.16.0-win-x64"
$env:Path = "$nodeDir;$env:Path"
& "$nodeDir\npm.cmd" run build
```

Expected: build completes successfully.

- [x] **Step 2: Run diff whitespace check**

```powershell
git diff --check
```

Expected: no whitespace errors. Existing CRLF warnings may still appear.

- [x] **Step 3: Update handoff files**

Record that the rule was implemented, note verification results, and move the task from active/next to done in `AGENTS_TODO.md`.

## Self-Review

- Spec coverage: the plan covers the vendor-prefix override, direct parser smoke check, build, diff check, and required handoff updates.
- Placeholder scan: no `TBD`, `TODO`, or vague future work remains.
- Type consistency: the plan uses existing `extract_fields()` return keys: `vendor`, `category`, and `invoice_type`.
