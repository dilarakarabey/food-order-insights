# Excel export

Read this reference before exporting analyzed order data to `.xlsx`.

## Fast path

Use the bundled `scripts/export_workbook.py`. It creates and verifies all sheets in one pass, derives period breakdowns from canonical orders, protects receipt text from formula injection, and does not access Gmail.

1. Reuse the normalized orders already extracted in this task. Do not rescan Gmail.
2. If the host exposes workspace dependency discovery, call it once and use the returned bundled Python executable. The bundled runtime includes `xlsxwriter`.
3. Create one compact UTF-8 JSON input containing only the contract below. Do not include raw messages or duplicate aggregate tables.
4. Run the exporter once:

```text
<bundled-python> <skill-directory>/scripts/export_workbook.py --input <compact-json> --output <requested-xlsx>
```

5. Return the workbook only after the exporter exits successfully. It performs archive and required-sheet checks itself.

Do not run `pip`, `uv`, `conda`, `npm`, Homebrew, or another installer. Do not download a library, switch repeatedly between spreadsheet skills, or rebuild the workbook interactively cell by cell. If the bundled runtime cannot be located or the one exporter attempt fails, report the concise failure and preserve the chat analysis; do not enter a fallback-install loop.

## Compact JSON contract

Use these top-level keys:

- `metadata`: `requested_scope`, `coverage_start`, `coverage_end`, `generated_at`, and `timezone`;
- `orders`: canonical normalized order objects, including nested `items`; omit private identifiers and raw email text;
- `key_patterns`: only eligible, already-supported observations shown in chat;
- `risk_report`: `scope_limitation`, `available_metrics`, and `not_derived` using the fields below;
- `recommendations`: Meal Prep and Lifestyle Change rows;
- `data_quality`: completed-scan coverage values not derivable from the orders alone.

Each available Risk Report metric may contain `metric`, `value`, `unit`, `numerator`, `denominator`, `window`, `coverage`, `comparison`, and `meaning_and_limit`. Each withheld metric may contain `metric`, `reason`, `needed`, `available_count`, `required_count`, `window`, and `coverage`.

Do not include Gmail IDs, thread IDs, provider order IDs, delivery addresses, phone numbers, recipients, payment fragments, tracking links, raw email content, or customer notes. The exporter rejects private identifier and raw-content keys. It also neutralizes strings that could be interpreted as spreadsheet formulas or links.

## Workbook structure

The exporter creates these sheets in order:

1. **Summary** — requested scope, coverage, unique canonical order count, spend by currency with amount coverage, and eligible key patterns.
2. **Orders** — one row per canonical order with an opaque sequential `order_ref`, dates, time basis, provider, restaurant, status, currency, receipt amounts, formula-derived net spend, calorie range and confidence, parse confidence, and warnings.
3. **Items** — one row per item/extra linked by `order_ref`, with receipt text separate from estimates and controlled-vocabulary matches.
4. **Period Breakdown** — script-derived counts and amounts by year, month, ISO week, weekday, and hour. Amount-coverage and calorie-coverage counts remain visible so blanks are not mistaken for zero.
5. **Risk Report** — available natural-unit metrics and **Not derived** rows with evidence counts and limitations. No composite score, grade, or arbitrary risk points.
6. **Recommendations** — Meal Prep and Lifestyle Changes with evidence, action, effort, prep time, progress measure, fallback, feedback status, and evidence limits.
7. **Data Quality** — computed order coverage plus completed-mailbox-scan values and their basis.

## Accuracy and privacy rules

- Keep currencies separate; never sum currencies without a user-authorized conversion source and visible rate.
- Keep receipt facts separate from estimates. Prefix estimated calorie fields with `estimated_` and store low/high bounds, never a false exact value.
- Leave unavailable amounts blank and expose coverage counts. Do not turn missing amounts into zero.
- Include only Risk Report metrics that passed their evidence gates. Preserve expected omissions as **Not derived** rows.
- Use a neutral filename such as `Food-Order-Insights-YYYY-MM-DD.xlsx` and do not upload it elsewhere without separate user authorization.
- The workbook reflects food-order emails, not confirmed consumption or the user's complete diet or lifestyle.
