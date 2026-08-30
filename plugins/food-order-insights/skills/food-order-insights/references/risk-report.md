# Risk Report

Read this reference when the user requests a Risk Report, risk scan, warning summary, or Findeks-like overview.

## Meaning

The **Order Pattern Risk Report** is a descriptive review of change opportunities visible in supported food-order emails. It is not a medical, nutritional, psychological, credit, or financial-risk assessment. It measures ordering records, not confirmed food consumption or the user's full lifestyle.

Do not produce a composite score, points, grade, percentile, traffic-light status, or population comparison. The available email data and product-defined thresholds do not validate such a number. Report each eligible metric in its natural unit with its numerator, denominator, time window, coverage, and limitation.

A **countable order** is one canonical placement order that has not been explicitly cancelled. Include status `placed` when the provider does not reliably send delivery confirmations; label completion as unknown. Include refunded or partially refunded orders unless a matched message says they were cancelled before fulfillment. Use net spend where available.

A **complete covered week** is a Monday-through-Sunday week wholly inside the requested scan interval for which the exact-sender search reached its final page without a tool failure. Count weeks with zero orders. Exclude partial boundary weeks and weeks affected by an unfinished search. A complete covered month follows the same rule for the first through last calendar day.

## Metric eligibility

Data-sufficiency thresholds below decide only whether the metric is stable enough to show. They are not health or behavioral thresholds.

### Order frequency

Show countable orders per complete covered week only with at least four complete covered weeks. Report total countable orders, complete weeks, and the arithmetic rate. Do not label the rate high or low. With fewer than four weeks, show the exact order count but mark the weekly rate **Not derived**.

### Late-order timing

Use the share of countable orders placed from 22:00 through 04:59 in the user's timezone. The denominator is orders with a usable analysis time.

A usable time is either the explicit receipt `ordered_at` or the Gmail timestamp of the canonical placement email when `ordered_at` is absent. Never use delivery, invoice, cancellation, refund, courier-update, or marketing timestamps.

Show this metric only when all are true:

- at least 10 countable orders have usable times;
- usable-time coverage is at least 80% of countable orders;
- at least four complete covered weeks are available.

Report `late orders / usable-time orders`, the percentage, and how many timestamps used the Gmail fallback. Call it an ordering-time pattern, not sleep disruption.

### Meal concentration

Normalize obvious spelling variants only; do not merge distinct dishes because they seem similar. Show the share of classifiable countable orders represented by the three most frequent dishes only when all are true:

- at least 10 countable orders are available;
- at least 80% contain a classifiable dish;
- the scan includes at least four complete covered weeks.

Report the three dish names, their individual counts, and `top-three orders / classifiable orders`. Do not interpret concentration as nutritional quality.

### Receipt-visible preparation signals

Use `balance-patterns.json` only as a controlled vocabulary. Normalize with Unicode NFKC, lowercase, replace punctuation with spaces, and collapse whitespace. Match whole tokens or phrases. Do not translate, stem, infer synonyms, or add terms during a scan.

A countable order is classifiable when at least one non-empty item name was extracted with parse confidence of `0.75` or higher. Count at most one hit per order when an item, variant, or extra explicitly matches `fried_preparation`, `sweetened_drink`, or `dessert`.

Show the metric only when all are true:

- at least 10 countable orders are classifiable;
- classifiable coverage is at least 80% of countable orders;
- at least four complete covered weeks are available.

Report `matched orders / classifiable orders`, the percentage, category counts, matched phrases, and vocabulary version. State that a non-match means only that the controlled phrase was not visible; it does not prove a meal was balanced or healthy.

### Spending and budget context

Always keep currencies separate. Exact gross and net totals may be shown when their source fields are available. Show average monthly net spend only with at least two complete covered calendar months; otherwise mark it **Not derived**.

Compare spend with a budget only when the user supplies a delivery budget in the same currency and cadence. Report the amount and percentage of that user-defined budget. Never infer income, affordability, debt, or financial distress. Without a budget, explain that budget pressure was not derived because no personal baseline was supplied.

### Trends

Derive a trend only when two adjacent, non-overlapping windows can each independently satisfy the metric's eligibility rules. Prefer the most recent four complete weeks versus the preceding four complete weeks. Each window must also contain at least six countable orders.

Report both window values and the absolute change; for shares, also report percentage-point change. Do not use `improving`, `worsening`, or causal language. If either window fails, mark the trend **Not derived** and state which window or field was insufficient.

## Report layout

Present:

1. a one-sentence scope and limitation;
2. coverage period, search completeness, countable-order count, status breakdown, and parse-confidence coverage;
3. an **Available metrics** table with metric, value, numerator/denominator, window, coverage, and what it does and does not mean;
4. up to two neutral observations supported by eligible metrics;
5. a **Not derived** table for expected metrics that failed a gate, with the exact reason and what additional data or user input would make each available;
6. up to three linked Lifestyle Changes, only when their underlying metric is eligible;
7. a plain statement that receipts omit home-cooked meals, groceries, exercise, sleep, medical history, and the rest of the user's diet.

Do not replace an ineligible metric with a model estimate. Do not create an overall label from the count or direction of available signals.
