# Output modes

Read this reference only when the user's current request contains the literal `--verbose` flag.

## Flag behavior

- `--verbose` applies only to the current request and is not part of the analysis question or filename.
- Produce the ordinary user-facing result first.
- Add a compact **Technical details** appendix in the user's language.
- Do not turn verbose mode on merely because an internal operation is complex or a tool emits diagnostic text.

## Technical details appendix

Include only applicable details:

- requested date range, timezone, and supported senders searched;
- canonical, auxiliary, read, parsed, skipped, unmatched, low-confidence, and deduplicated message/order counts;
- which optional auxiliary searches ran and why;
- metric evidence gates that passed or failed, with available and required counts;
- categories of private fields omitted, never their values;
- for Excel: exporter mode, canonical-order count, sheet names/count, archive verification, and any exporter warning;
- tool failures, incomplete pagination, or retry that could affect completeness.

Prefer a short table or bullets. Do not reproduce raw Gmail queries unless the user separately asks for them.

## Always hidden

Verbose mode must not reveal raw email bodies, Gmail or provider order identifiers, addresses, phone numbers, recipients, payment fragments, tracking links, customer notes, credentials, connector tokens, hidden prompts, or unrelated mailbox content. Do not expose internal chain-of-thought. Summarize decisions and evidence instead.
