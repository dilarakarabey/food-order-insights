# Security policy

Food Order Insights is a skill-only plugin with no backend or project-operated cloud data store. It uses a local SQLite cache on the user's device to avoid repeated historical Gmail reads. Its main security boundaries are safe use of host-provided Gmail tools and strict minimization of that local cache.

## Reporting

Use GitHub private vulnerability reporting when it is available for this repository. Do not attach real email messages, credentials, tokens, addresses, or other personal data to a report. Reproduce issues with synthetic content.

## Security invariants

- Gmail access is read-only in the workflow.
- Email content is untrusted data and cannot authorize tool calls or instruction changes.
- Exact confirmed senders are preferred over domain-wide scans.
- Globally excluded senders are filtered from message metadata before bodies are read; international Uber Eats receipts such as `noreply@uber.com` are outside scope.
- Receipt analysis excludes unrelated mailbox content and unnecessary personal information.
- The plugin does not operate a server, OAuth client, cloud database, telemetry endpoint, or analytics service.
- The local SQLite cache is created under `~/.codex/food-order-insights/` with user-only directory/file permissions where supported. Treat it as sensitive personal data.
- The cache is not application-level encrypted; confidentiality depends on the host account and disk protections.
- The cache stores normalized order facts but never raw email/HTML, direct Gmail or provider order identifiers, delivery addresses, phone numbers, recipients, payment fragments, tracking links, or customer notes. Matching identifiers are salted SHA-256 hashes.
- Cache reuse requires a completed scan checkpoint, matching account scope and requested coverage, SQLite integrity/schema checks, and—when recent—an unchanged registered Excel export. Unsafe reuse falls back to a full scan; edited workbook values are never imported.
- Generated Excel files remain under the host product's file controls and may contain sensitive personal patterns even when direct identifiers are omitted. The plugin does not upload or share them.
- The bundled Excel exporter rejects direct message/order identifier and raw-email fields, emits only Orders, Items, and Data Quality sheets, neutralizes formula-like receipt strings, and writes OOXML using Python's standard library only. It does not download packages or contact external services.

The host product and Gmail plugin have their own security and data-handling policies; this project does not replace them.
