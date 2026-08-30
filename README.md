# Food Order Insights

An open-source ChatGPT/Codex plugin that analyzes food-delivery receipts through the user's connected Gmail plugin—without running its own backend, storing email, or asking users to download receipts.

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
- a transparent, non-medical Order Pattern Risk Score with factor-level evidence and data-confidence gating;
- a Lifestyle Changes view with small experiments, effort, fallback options, and progress against the user's own baseline;
- an `.xlsx` export with orders, items, period breakdowns, Risk Report, recommendations, and data-quality sheets.

## Why a plugin instead of an app?

Food Order Insights is intentionally a skill-only plugin:

```text
Connected Gmail plugin
        |
        v
Food Order Insights skill
  - sender discovery
  - receipt extraction
  - aggregation
  - cautious food insights
  - explainable risk scan
  - lifestyle experiments
        |
        v
Chat response, visualization, or Excel workbook
```

There is no Food Order Insights server, account system, database, OAuth client, or analytics service. Gmail authorization and model execution stay with the host product. The repository contains only instructions, schemas, provider definitions, and synthetic test fixtures.

OpenAI's plugin architecture supports skill-only plugins and allows an MCP server or custom UI to be added later if the project ever needs one. See the [official plugin architecture documentation](https://developers.openai.com/plugins/concepts/plugins).

## Requirements

- A ChatGPT or Codex surface that supports plugins/skills.
- The Gmail plugin installed and connected with permission to search and read mail.
- A host file-generation capability is required only for `.xlsx` export.
- No OpenAI API key and no Food Order Insights account.

If Gmail tools are unavailable, the skill asks the user to connect Gmail. It does not fall back to requesting downloaded receipt files.

## Install for local development

Until the plugin is published in the universal plugin directory, clone this repository and add it as a repository marketplace:

```bash
codex plugin marketplace add /absolute/path/to/food-order-insights
```

Then install **Food Order Insights** and ensure the separate Gmail plugin is connected.

## Current provider coverage

The initial registry includes a user-confirmed Trendyol Yemek sender:

```text
infotrendyolgo@mail.trendyolgo.com
```

Uber Eats and GetirYemek are included as discovery targets until contributors confirm their actual receipt sender addresses. The skill performs a small candidate search first and does not broadly scan an unconfirmed sender.

Provider behavior lives in [providers.json](plugins/food-order-insights/skills/food-order-insights/references/providers.json). Contributions should add verified sender addresses and synthetic fixtures rather than real emails.

## Privacy and safety

- Uses Gmail search/read capabilities only; never sends, labels, archives, trashes, or deletes email.
- Searches exact confirmed senders for full scans.
- Treats email bodies as untrusted data and ignores instructions embedded in them.
- Does not expose delivery addresses, phone numbers, recipients, tracking links, or unrelated message content.
- Does not maintain its own storage or telemetry.
- Describes calories as estimates and gives ranges with confidence.
- Provides general food-pattern observations and meal ideas, not diagnosis or medical treatment.
- Calls its score an Order Pattern Risk Score: a visible, editable product heuristic rather than a medical, credit, insurance, or financial-risk score.
- Suppresses the score when there are fewer than 12 completed orders, less than 8 weeks of coverage, or insufficient high-confidence data.
- Omits Gmail IDs, order IDs, raw email text, and customer notes from Excel by default.
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
    └── references/
        ├── providers.json
        ├── receipt-schema.json
        ├── insight-rules.md
        ├── balance-patterns.json
        ├── risk-report.md
        └── excel-export.md
tests/fixtures/
```

## Roadmap

- Validate cross-plugin Gmail access on public ChatGPT and Codex surfaces.
- Confirm sender addresses and receipt formats for Trendyol Yemek, GetirYemek, and Uber Eats.
- Add robust synthetic evaluation fixtures for discounts, extras, notes, refunds, and multiple currencies.
- Improve in-conversation charts, literal interactive tabs, and feedback continuity.
- Package the same schema and analysis rules for Gemini where its extension model permits.
- Consider an optional MCP UI only if native chat visualizations are insufficient.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Never submit a real receipt, email address belonging to a person, delivery address, phone number, order ID, or authentication token.

## License

[MIT](LICENSE)
