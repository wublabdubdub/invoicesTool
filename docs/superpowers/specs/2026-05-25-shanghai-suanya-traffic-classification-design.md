# Shanghai Suanya Traffic Classification Design

## Goal

Invoices whose recognized seller/vendor starts with `上海蒜芽科技` should be categorized as `城市间交通`.

## Scope

- Apply the rule during OCR field extraction in `scripts/ocr.py`.
- Match only the recognized `vendor` field, not arbitrary OCR text.
- Treat the match as a prefix match so variants such as `上海蒜芽科技有限公司` are included.
- Leave `invoice_type`, date, amount, tax, total, invoice number, and vendor tax ID unchanged.
- Do not change database schema, import flow, export flow, or renderer UI.

## Architecture

`scripts/ocr.py` already computes `vendor`, then derives `category` from OCR text keywords and returns both fields. Add a small vendor-prefix override after the existing category keyword classification and before the return object. This keeps the rule close to the OCR classification source while allowing Electron import, filtering, and export to continue using the saved OCR category normally.

## Testing

Use a direct Python smoke check against `extract_fields()` with representative OCR lines:

- `上海蒜芽科技有限公司` as the vendor should return `category == '城市间交通'`.
- The same sample should keep the existing `invoice_type` result from keyword parsing.

Run the project build after code changes using the documented `npm.cmd run build` command.

## Self-Review

- No placeholder sections remain.
- The rule is intentionally narrow and does not affect invoices where `上海蒜芽科技` only appears outside the recognized vendor.
- The design is consistent with the current OCR data flow: Python returns category, Electron persists it.
