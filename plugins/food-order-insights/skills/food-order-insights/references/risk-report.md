# Risk Report

Read this reference when the user requests a Risk Report, risk scan, score, warning level, or Findeks-like summary.

## Meaning and evidence gate

The report is an explainable scan of **order-pattern change opportunities visible in delivery receipts**. It is not a medical, nutritional, psychological, credit, or financial-risk assessment.

Calculate an overall Order Pattern Risk Score only when all of these are true:

- at least 12 completed orders are available;
- the scan covers at least 8 complete calendar weeks;
- at least 75% of completed orders have parse confidence of `0.75` or higher;
- at least three of the four non-budget factors below are eligible.

Otherwise show `Insufficient data` instead of a score. Still report coverage, directly observed facts, and which evidence gate failed.

## Factors

Use completed orders only. Treat the thresholds as transparent product defaults, not scientific or population norms.

A **complete covered week** is a Monday-through-Sunday week wholly inside the requested scan interval for which the exact-sender search completed through its final pagination page without a tool failure. Successful pagination is normal. Count weeks with zero orders. Exclude partial boundary weeks and any week affected by failed or unfinished pagination. Use this same definition for the evidence gate, delivery-reliance denominator, and workbook export.

### 1. Delivery reliance — maximum 25 points

Calculate completed orders placed inside complete covered weeks divided by the number of complete covered weeks:

| Orders per week | Points |
|---:|---:|
| `<= 1` | 0 |
| `> 1` and `<= 2` | 8 |
| `> 2` and `<= 4` | 16 |
| `> 4` | 25 |

### 2. Schedule disruption — maximum 20 points

Use the share of completed orders with a **usable analysis order time** placed from 22:00 through 04:59 in the user's timezone. The denominator is completed orders with a usable time, not all completed orders.

A time is usable when it is either:

1. the explicit receipt `ordered_at` value; or
2. the Gmail message timestamp from the original placed/order-confirmation receipt when `ordered_at` is absent.

Do not use the timestamp of a delivery, cancellation, refund, courier-update, or marketing message as order time. Track `receipt` versus `message_fallback` as the time basis. A message fallback remains usable but inherits the receipt's `-0.05` confidence deduction.

| Late-hour share | Points |
|---:|---:|
| `< 10%` | 0 |
| `>= 10%` and `< 20%` | 7 |
| `>= 20%` and `< 35%` | 14 |
| `>= 35%` | 20 |

Call this a schedule signal, not a sleep measurement. If order time is unavailable for more than 25% of completed orders, mark the factor ineligible.

### 3. Meal concentration — maximum 20 points

Normalize only obvious spelling variants; do not merge distinct dishes merely because they seem similar. Calculate the share of classifiable completed orders represented by the three most frequent dishes:

| Top-three dish share | Points |
|---:|---:|
| `< 35%` | 0 |
| `>= 35%` and `< 50%` | 7 |
| `>= 50%` and `< 70%` | 14 |
| `>= 70%` | 20 |

If fewer than 75% of completed orders contain a classifiable dish, mark the factor ineligible.

### 4. Repeated balance opportunities — maximum 20 points

Use `balance-patterns.json` as the controlled vocabulary. Normalize both the controlled phrases and visible item, variant, and extra names with Unicode NFKC normalization, lowercase them, replace punctuation with spaces, and collapse whitespace. Match whole tokens or whole phrases only. Do not translate, stem, infer synonyms, or add terms during a scan.

A completed order is classifiable when at least one non-empty item name was extracted with parse confidence of `0.75` or higher. Mark at most one hit per classifiable order when any normalized item, variant, or extra matches a phrase in `fried_preparation`, `sweetened_drink`, or `dessert`. Record the matched category and phrase. A non-match means only that no controlled phrase was visible; it does not prove the meal was balanced.

| Share with a balance opportunity | Points |
|---:|---:|
| `< 25%` | 0 |
| `>= 25%` and `< 40%` | 7 |
| `>= 40%` and `< 60%` | 14 |
| `>= 60%` | 20 |

If fewer than 75% of completed orders are classifiable by the rule above, mark the factor ineligible. Show the classified-order denominator, the controlled-vocabulary version, and the share of hits based on explicit phrases. Other model-inferred food observations may appear in narrative recommendations but must not change this score.

### 5. User-budget pressure — optional, maximum 15 points

Include this factor only when the user supplies a monthly delivery budget. Compare average monthly net delivery spend with that budget:

| Budget used | Points |
|---:|---:|
| `<= 100%` | 0 |
| `> 100%` and `<= 110%` | 5 |
| `> 110%` and `<= 125%` | 10 |
| `> 125%` | 15 |

Never infer income, affordability, debt, or financial distress. Without a user-supplied budget, omit this factor from both numerator and denominator.

## Score and labels

Sum eligible factor points and divide by the sum of their maximum points:

```text
score = round(100 * eligible_points / eligible_max_points)
```

| Score | Label |
|---:|---|
| 0–24 | Lower signal |
| 25–49 | Emerging signal |
| 50–74 | Elevated signal |
| 75–100 | Strong signal |

Avoid red/green moral framing. Always show the point contribution of every eligible factor and name ineligible factors.

## Trend and report layout

When both windows contain at least six completed orders, compare the most recent four complete weeks with the preceding four complete weeks. Show direction for each factor as `improving`, `stable`, or `increasing`, but do not invent a trend when the factor cannot be recomputed for both periods.

Present:

1. score or `Insufficient data`, label, and a one-sentence limitation;
2. coverage period, completed-order count, and usable-order share;
3. factor table with measure, threshold band, points, maximum, confidence, and trend;
4. the top two contributing signals in neutral language;
5. up to three linked Lifestyle Changes;
6. a plain statement that receipts do not capture home-cooked meals, groceries, exercise, sleep, medical history, or the full diet.
