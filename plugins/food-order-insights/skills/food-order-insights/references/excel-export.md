# Excel export

Read this reference before exporting analyzed order data to `.xlsx`.

## Fast path

Use the bundled `scripts/export_workbook.py`. It creates and verifies the three compact sheets in one pass, protects receipt text from formula injection, and does not access Gmail. Its bundled `minimal_xlsx.py` writer uses only Python's standard library.

1. Apply `local-cache.md`. If the cache is valid, use `order_cache.py export-payload` for the requested range. Otherwise use the normalized orders from the completed current scan.
2. Use an already available Python 3.10+ executable. Do not invoke a spreadsheet artifact runtime or dependency loader: no third-party package is required.
3. Create one compact UTF-8 JSON input containing only `orders` and optional `data_quality`. Do not include raw messages or aggregate tables for removed sheets.
4. Run the exporter once. Add the final `--verbose` argument only when the user's current request explicitly contains `--verbose`:

```text
<bundled-python> <skill-directory>/scripts/export_workbook.py --input <compact-json> --output <requested-xlsx>
```

5. After success, register the workbook with `order_cache.py register-export`. Return it only after the exporter exits successfully.

Do not run `pip`, `uv`, `conda`, `npm`, Homebrew, or another installer. Do not import or require `xlsxwriter`, `openpyxl`, or another spreadsheet package at runtime. Do not switch repeatedly between spreadsheet skills or rebuild the workbook interactively cell by cell. If Python 3.10+ cannot be located or the one exporter attempt fails, report the concise failure and preserve the chat analysis; do not enter a fallback-install loop.

## User-facing response

In default mode, return the workbook link/path plus a short summary. Do not state that PII was excluded, describe cache mechanics or the compact JSON handoff, name the runtime or library, enumerate validation steps, or explain temporary-file handling.

With `--verbose`, keep the workbook result first and add the technical appendix defined in `output-modes.md`. Include the exporter's structured diagnostics and any warning or failure without exposing omitted values, identifiers, cache hashes, or salts.

## Compact JSON contract

Use these top-level keys:

- `orders`: canonical normalized orders with nested items, restricted to fields used below;
- `data_quality`: completed-scan coverage values not derivable from order rows.

Do not include Gmail IDs, thread IDs, provider order IDs, delivery addresses, phone numbers, recipients, payment fragments, tracking links, raw email content, or customer notes. The exporter rejects private identifier and raw-content keys and neutralizes strings that could be interpreted as spreadsheet formulas or links.

## Workbook structure

The exporter creates exactly these sheets in order:

1. **Orders** — `order_ref`, `ordered_at`, `message_received_at`, `provider`, `status`, `currency`, `food_subtotal`, `delivery_fee`, `discount`, `total_paid`.
2. **Items** — `order_ref`, `item_name`, `quantity`.
3. **Data Quality** — compact coverage facts and their basis. A confidence result is included only when confidence values were actually supplied.

The workbook deliberately does not contain Summary, Period Breakdown, Risk Report, or Recommendations sheets. Those capabilities remain available in chat without duplicating them in every export.

## Accuracy and privacy rules

- Keep currencies separate; never sum currencies without a user-authorized conversion source and visible rate.
- Leave unavailable amounts blank. Do not turn missing amounts into zero.
- Use a neutral filename such as `Food-Order-Insights-YYYY-MM-DD.xlsx` and do not upload it elsewhere without separate user authorization.
- The workbook reflects food-order emails, not confirmed consumption or the user's complete diet or lifestyle.
- Register the finished file for integrity checks, but never import workbook edits into the normalized cache.
