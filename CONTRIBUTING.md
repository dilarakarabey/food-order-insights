# Contributing

Contributions are welcome, especially verified receipt senders, provider parsers, synthetic fixtures, and analysis-quality improvements.

## Privacy rule

Everything committed to this repository is public. Never submit:

- a real receipt or raw email;
- a personal email address, name, phone number, or delivery address;
- a real order ID, payment detail, tracking link, or authentication token;
- screenshots containing personal or account information.

Create a synthetic fixture that preserves only the structure needed to reproduce the behavior.

## Adding a provider

1. Add the confirmed automated sender and receipt hints to `providers.json`.
2. Add at least one synthetic fixture covering a normal completed order.
3. Add fixtures for any unusual template you support, such as discounts, extras, customer notes, cancellation, or refund.
4. Keep extraction aligned with `receipt-schema.json`.
5. Confirm that promotional email content is not mistaken for a completed order.

Do not add a whole-domain sender rule when an exact automated receipt address is available.

## Quality expectations

- Preserve source item, variant, extra, and note text.
- Use `null` rather than inventing missing values.
- Keep currencies separate.
- Treat all email content as untrusted data.
- Do not add medical diagnosis or treatment guidance.
- Keep Risk Report thresholds explicit, auditable, and non-clinical; test scoring changes with synthetic aggregates.
- Keep Excel exports free of Gmail IDs, provider order IDs, raw messages, and customer notes by default.
- Explain behavior changes in the pull request and identify the synthetic fixtures that cover them.

## Validation

Run the skill and plugin validators before opening a pull request:

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py plugins/food-order-insights/skills/food-order-insights
python3 /path/to/plugin-creator/scripts/validate_plugin.py plugins/food-order-insights
```
