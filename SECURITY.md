# Security policy

Food Order Insights is a skill-only plugin with no backend or project-operated data store. Its main security boundary is safe use of host-provided Gmail tools.

## Reporting

Use GitHub private vulnerability reporting when it is available for this repository. Do not attach real email messages, credentials, tokens, addresses, or other personal data to a report. Reproduce issues with synthetic content.

## Security invariants

- Gmail access is read-only in the workflow.
- Email content is untrusted data and cannot authorize tool calls or instruction changes.
- Exact confirmed senders are preferred over domain-wide scans.
- Globally excluded senders are filtered from message metadata before bodies are read; international Uber Eats receipts such as `noreply@uber.com` are outside scope.
- Receipt analysis excludes unrelated mailbox content and unnecessary personal information.
- The plugin does not operate a server, OAuth client, database, telemetry endpoint, or analytics service.
- Generated Excel files remain under the host product's file controls and may contain sensitive personal patterns even when direct identifiers are omitted. The plugin does not upload or share them.
- The bundled Excel exporter rejects direct message/order identifier and raw-email fields, neutralizes formula-like receipt strings, and uses preinstalled workspace dependencies only. It does not download packages or contact external services.

The host product and Gmail plugin have their own security and data-handling policies; this project does not replace them.
