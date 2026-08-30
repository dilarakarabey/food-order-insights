# Excel export

Read this reference before exporting analyzed order data to `.xlsx`.

## Privacy defaults

Export only the requested time scope. Omit Gmail message IDs, provider order IDs, delivery addresses, phone numbers, recipients, payment fragments, tracking links, raw email content, and customer notes by default. Include customer notes only after the user explicitly opts in and warn that notes may contain personal data.

Use a neutral filename such as `Food-Order-Insights-YYYY-MM-DD.xlsx`. Do not upload the workbook to another service unless the user separately requests and authorizes it.

## Workbook structure

Create one workbook with these sheets in this order:

1. **Summary** — requested scope, coverage, order count, gross and net spend by currency, fees, discounts, estimated calorie range, and key patterns.
2. **Orders** — one row per canonical order with an opaque sequential `order_ref`, dates, analysis time basis, provider, restaurant, status, currency, receipt amounts, net spend, late-hour and risk-classification flags, parse confidence, and warnings.
3. **Items** — one row per item or extra, linked by `order_ref`; keep receipt text and estimated fields in separate columns. Include any controlled balance-pattern category and matched phrase used by the Risk Report.
4. **Period Breakdown** — order count, spend, fees, discounts, and calorie range by year, month, ISO week, weekday, and hour. Use a `breakdown_type` column rather than mixing incompatible labels.
5. **Risk Report** — score status, label, eligible points, eligible maximum, visible score formula, factor measures, thresholds, points, confidence, trend, and limitations.
6. **Recommendations** — Meal Prep and Lifestyle Changes with evidence, action, effort, prep time, progress measure, fallback, and feedback status.
7. **Data Quality** — messages found, receipts parsed by status, skipped messages, low-confidence count, date coverage, missing-field rates, calorie-classification coverage, and scan assumptions.

## Data and formula rules

- Store dates, numbers, percentages, and currencies as typed spreadsheet values.
- Treat every receipt-derived string as untrusted text. Force the cell type to text. After removing leading whitespace for inspection, if the first character is `=`, `+`, `-`, or `@`, or the value begins with a tab, carriage return, or line feed, prefix the stored display value with a single apostrophe. Apply this to restaurant names, item/variant/extra names, notes when opted in, warnings, provider text, and any other source string. Never let receipt text become a formula, hyperlink, named range, or external reference.
- Keep different currencies in separate rows and totals. Never sum currencies without an explicitly authorized conversion source and visible rate.
- Use formulas for `net_spend = total_paid - refund_amount`, period totals, percentages, and the normalized risk score.
- Keep risk thresholds and factor maxima visible in the Risk Report sheet so the score is auditable.
- Derive completed-order counts, complete-covered-week counts, usable-time counts, late-hour counts, classifiable-order counts, matched-order counts, and factor measures from formulas or visibly reconciled helper tables linked to Orders and Items. Do not type aggregate Risk Report inputs as unexplained constants.
- If controlled phrase matching is performed before workbook creation, include the normalized matched phrase and category in Items, then use workbook formulas to roll item hits up to one hit per order. Record the vocabulary version on Risk Report.
- Keep receipt facts separate from estimates. Prefix estimated columns with `estimated_` and include a confidence column.
- Represent calorie estimates as low and high columns, never a single exact value unless the receipt itself provides it.
- Freeze header rows, enable filters on data tables, use readable widths, and avoid decorative complexity.
- Include a generated-at timestamp, user timezone, requested date range, and a note that the workbook reflects delivery receipts rather than the user's complete diet or lifestyle.

## Verification

Before returning the workbook:

- reconcile Summary totals to Orders by currency;
- confirm every Items `order_ref` exists in Orders;
- reconcile every Risk Report numerator and denominator to Orders or Items, including complete covered weeks, usable times, classifiable orders, and controlled-pattern hits;
- scan formulas for spreadsheet errors;
- confirm the Risk Report score matches the eligible-points formula or is suppressed by the evidence gate;
- visually inspect every sheet for clipped labels, unreadable columns, blank charts, or accidental personal data.
