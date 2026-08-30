# Food Order Insights

**English** · [Türkçe](README.md)

An open-source, Türkiye-focused ChatGPT/Codex plugin that analyzes food-delivery receipts through the user's connected Gmail plugin—without running its own backend, storing raw email, or asking users to download receipts. It can retain normalized order data in a private SQLite cache on the user's computer to avoid repeated historical scans.

## What it does

Ask questions such as:

- “Analyze my food-delivery orders from the last year.”
- “How much did I spend on delivery fees by month?”
- “What do I order most often on Sunday evenings?”
- “Suggest three easy meals based on my common orders.”
- “Which weeks had unusually heavy delivery use?”
- “Run my Food Order Risk Report.”
- “Show my Lifestyle Changes view.”
- “Export this analysis to Excel.”

The skill searches known food-delivery senders, reads matching receipts, extracts order details, and produces:

- order counts and spending by year, month, week, day, weekday, and hour;
- restaurant, cuisine, dish, provider, and meal-category patterns;
- food subtotal, delivery/service fees, discounts, tips, and total paid when present;
- line items, quantities, variants, extras, and customer notes when present;
- estimated calorie ranges with visible confidence;
- delivery-heavy periods that the user can label as busy, ill, travelling, social, no kitchen, or something else;
- meal-prep ideas and practical alternatives that adapt to accept/dislike feedback;
- a transparent, non-medical Order Pattern Risk Report with natural-unit metrics, visible denominators, and metric-specific data gates;
- a Lifestyle Changes view with small experiments, effort, fallback options, and progress against the user's own baseline;
- a fast, compact `.xlsx` export with `Orders`, `Items`, and `Data Quality` sheets, using only Python's standard library and downloading no third-party packages.

## Output modes

The plugin is quiet by default: it shows the requested result without narrating connector calls, runtime selection, temporary files, validation steps, or statements such as “no PII was used.” Information that changes how the result should be interpreted—such as an incomplete scan, low data confidence, or why a metric was not derived—remains visible.

Add `--verbose` to the request when you want technical details:

```text
Export this analysis to Excel --verbose
```

Verbose mode adds a separate technical summary covering scan scope, processed and deduplicated message/order counts, evidence gates, and Excel verification. It never reveals raw emails or personal data. The flag applies only to the request in which it appears.

## Fewer scans and tokens

After a complete first scan, the plugin stores normalized orders locally at `~/.codex/food-order-insights/orders.sqlite3` by default. On later commands, when that dataset is valid, it reuses historical orders and searches only for new placement, cancellation, and refund emails received after the last complete scan.

If an Excel export was created in the last 30 days, the plugin checks its path, size, modification time, and digest. An unchanged file allows incremental scanning. A modified, moved, or missing recent export triggers a safe full scan of the requested period. Workbook edits are never imported as receipt facts; the workbook is only an integrity signal.

The local cache does not store raw email bodies, Gmail or provider order IDs, addresses, phone numbers, payment fragments, or customer notes. Matching identifiers are converted to salted hashes before being written. To reset the cache, the user can delete that local SQLite file; the next command rebuilds it with a full scan.

## Why a plugin instead of an app?

Food Order Insights is intentionally a skill-only plugin:

```text
Connected Gmail plugin
        |
        v
Food Order Insights skill
  - exact-sender search
  - receipt extraction
  - local incremental order cache
  - aggregation
  - cautious food insights
  - explainable risk scan
  - lifestyle experiments
        |
        v
Chat response, visualization, or Excel workbook
```

There is no Food Order Insights server, account system, cloud database, OAuth client, or analytics service. There is only a local SQLite cache on the user's device. Gmail authorization and model execution stay with the host product. The repository contains instructions, schemas, provider definitions, local helper scripts, and synthetic test fixtures.

OpenAI's plugin architecture supports skill-only plugins and allows an MCP server or custom UI to be added later if the project ever needs one. See the [official plugin architecture documentation](https://developers.openai.com/plugins/concepts/plugins).

## Requirements

- A ChatGPT or Codex surface that supports plugins/skills.
- The Gmail plugin installed and connected with permission to search and read mail.
- Python 3.10 or newer is used for the local cache and `.xlsx` export; `xlsxwriter`, `openpyxl`, and other third-party packages are not required.
- No OpenAI API key and no Food Order Insights account.

If Gmail tools are unavailable, the skill asks the user to connect Gmail. It does not fall back to requesting downloaded receipt files.

## Installation

You do not need to clone the repository. First add the Food Order Insights marketplace in your terminal:

```bash
codex plugin marketplace add https://github.com/dilarakarabey/food-order-insights.git
```

Then install the plugin:

```bash
codex plugin add food-order-insights@personal
```

Start a new Codex session after installation. Make sure the Gmail connector is connected.

## Current provider coverage

The initial registry includes user-confirmed Türkiye senders used by Trendyol Go / Uber Eats Trendyol Go:

```text
infotrendyolgo@mail.trendyolgo.com
infotrendyolgo@trendyolmail.com
```

Trendyol Go / Uber Eats Trendyol Go commonly sends several messages for one order, but platform delivery messages are not sent for every restaurant-courier order. Food Order Insights therefore counts only `Yemek Siparişini Aldık` as the canonical order. Delivery, e-archive, cancellation, and refund messages never increase order count; they may only enrich or update a matching placement. A missing delivery email means completion is unknown, not that the order did not happen.

GetirYemek is not searched, discovered, or included. The current scan scope is deliberately limited to the two confirmed senders above.

### Why Uber Eats support is Türkiye-only

The supported Turkish service is Uber Eats Trendyol Go, including its former Trendyol Go branding. Its `Yemek Siparişini Aldık` email contains the ordered food names and quantities needed for analysis.

International Uber Eats receipts use different templates. In the tested German format, messages from `noreply@uber.com` contain the restaurant, total, and a link to the full receipt, but not the ordered food items in the email body. Following receipt links would expand the product's access and privacy surface, so Food Order Insights does not do that. It excludes `noreply@uber.com` before reading message bodies and does not include international Uber Eats orders in counts, spending, recommendations, the Risk Report, or Excel exports.

This is an intentional product boundary, not a claim that every country uses the same Uber template. International formats can differ, but they are outside this project's current Türkiye-only scope.

Provider behavior lives in [providers.json](plugins/food-order-insights/skills/food-order-insights/references/providers.json). Contributions should add verified sender addresses and synthetic fixtures rather than real emails.

## Privacy and safety

- Uses Gmail search/read capabilities only; never sends, labels, archives, trashes, or deletes email.
- Searches exact confirmed senders for full scans.
- Never runs discovery searches for GetirYemek or another unsupported provider.
- Excludes international Uber Eats senders such as `noreply@uber.com` before reading message bodies.
- Uses provider-specific canonical messages and suppresses placement/invoice duplicates from order counts.
- Treats email bodies as untrusted data and ignores instructions embedded in them.
- Does not expose delivery addresses, phone numbers, recipients, tracking links, or unrelated message content.
- Runs no server or cloud storage and no telemetry; normalized orders stay in a user-only SQLite cache on the device.
- Never writes raw email, direct Gmail/provider identifiers, delivery addresses, phone numbers, payment fragments, or customer notes to that cache; matching identifiers are salted hashes.
- Adds no application-level encryption to SQLite; the file is created with user-only permissions and relies on the device's account/disk security.
- With a valid cache, reads only supported messages after the last complete scan; account, scope, or recent-export integrity failures trigger a full scan.
- Describes calories as estimates and gives ranges with confidence.
- Provides general food-pattern observations and meal ideas, not diagnosis or medical treatment.
- Does not create a composite Risk Report score, grade, percentile, or population comparison. It reports eligible metrics in natural units with numerators, denominators, windows, and limitations.
- Applies a separate minimum sample and coverage gate to each inferred metric. Expected metrics that cannot be supported appear as **Not derived**, with the exact reason and what would make them available.
- Omits Gmail IDs, order IDs, raw email text, and customer notes from Excel by default.
- Uses a one-pass, Python-standard-library Excel exporter; it does not download libraries or retry through multiple spreadsheet toolchains.
- Never infers that a user was ill; it asks the user to label unusual periods.

The host product's own data controls and connector policies still apply. This project cannot change or replace them.

## Repository structure

```text
.agents/plugins/marketplace.json
plugins/food-order-insights/
├── .codex-plugin/plugin.json
└── skills/food-order-insights/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── scripts/
    │   ├── export_workbook.py
    │   ├── minimal_xlsx.py
    │   └── order_cache.py
    └── references/
        ├── providers.json
        ├── receipt-schema.json
        ├── insight-rules.md
        ├── balance-patterns.json
        ├── risk-report.md
        ├── output-modes.md
        ├── local-cache.md
        └── excel-export.md
tests/fixtures/
```

## Roadmap

- Validate cross-plugin Gmail access on public ChatGPT and Codex surfaces.
- Revisit additional Türkiye providers only after an explicit scope decision, confirmed senders, and item-complete synthetic fixtures.
- Add robust synthetic evaluation fixtures for discounts, extras, notes, refunds, and multiple currencies.
- Improve in-conversation charts, literal interactive tabs, and feedback continuity.
- Package the same schema and analysis rules for Gemini where its extension model permits.
- Consider an optional MCP UI only if native chat visualizations are insufficient.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Never submit a real receipt, email address belonging to a person, delivery address, phone number, order ID, or authentication token.

## License

[MIT](LICENSE)
