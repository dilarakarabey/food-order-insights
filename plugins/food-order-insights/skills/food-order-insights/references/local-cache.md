# Local incremental cache

Read this reference before any Gmail scan. The cache reduces repeated mailbox reads and token use while keeping normalized order history on the user's device.

## Storage boundary

Use the bundled `scripts/order_cache.py` and its default database at `~/.codex/food-order-insights/orders.sqlite3`. It uses Python's standard library only and creates the directory and file with user-only permissions when the operating system permits.

The cache may contain normalized order facts needed for analysis, including dates, provider, restaurant, status, amounts, item names, variants, extras, calorie ranges, and confidence values. It must never contain raw email or HTML bodies, Gmail message/thread IDs, provider order IDs, delivery addresses, phone numbers, recipients, payment fragments, tracking links, or customer notes. The script converts the three matching identifiers to salted hashes before writing them. Never put the cache in the repository, an Excel workbook, or a cloud service.

If the user explicitly asks to inspect customer notes or another deliberately uncached field, run a narrowly scoped receipt scan for that request and do not persist the field.

## Reuse decision

1. Resolve the requested date range and capture a UTC `scan_started_at` immediately before any Gmail query.
2. Obtain a stable account scope from the connected Gmail host, such as its account or connection identifier. Pass it to the cache script; the script stores only its salted hash. If no stable account scope is available, do not reuse a persistent cache across sessions—continue with the ordinary scan and in-task dataset.
3. Check the cache before searching Gmail:

```text
python3 scripts/order_cache.py status --account-scope <stable-scope> --scope-start <requested-start>
```

4. Reuse only when `usable` is `true`. This means the SQLite integrity/schema check passed, the account scope matches, the cache covers the requested start, a complete scan checkpoint exists, and any registered export created in the last 30 days still has the same path, size, modification time, and SHA-256 hash.
5. If reusable, load the requested cached snapshot, then search the exact supported placement and relevant cancellation/refund subjects with Gmail `after:<scan_after_unix>`. Merge those new or updated records into the cached snapshot. This overlap-safe checkpoint comes from the last complete scan, not from workbook cells.
6. If the cache is missing, corrupt, from another account, too narrow, lacks a completed checkpoint, or has a recent export that is missing or modified, perform the normal full scan for the requested scope. Never import user-edited workbook contents into the cache.

Cache failure must not prevent the requested analysis. Fall back to the ordinary Gmail workflow without installing packages or exposing internal error details in quiet mode.

## Completing a scan

After pagination and all required auxiliary searches finish, ingest one compact normalized payload:

```json
{
  "scan": {
    "account_scope": "stable host-provided scope",
    "complete": true,
    "full_rescan": false,
    "checkpoint_at": "scan_started_at in UTC",
    "coverage_start": "requested or incremental start",
    "coverage_end": "scan_started_at in UTC"
  },
  "orders": []
}
```

If the handoff payload must be written to a temporary file, restrict it to the current user and remove it immediately after the ingest attempt. Do not retain raw identifiers in logs or verbose output.

Set `full_rescan` to `true` when the normal full requested scope was scanned. This also retires an invalid old export registration so it cannot force repeated full scans. Set `complete` to `true` only after every required page was read; an incomplete or failed scan may store successfully parsed rows but must not advance the checkpoint.

The Gmail message timestamp, not the order timestamp, controls incremental search boundaries. Incremental results must still follow the provider's canonical-placement and auxiliary-message matching rules. New cancellation or refund mail may update a cached order but must never create another order count.

## Excel registration

For an export, first create the minimal payload with `order_cache.py export-payload` when the cache is valid. After the workbook succeeds, register it:

```text
python3 scripts/order_cache.py register-export --path <created-xlsx>
```

The workbook is only an integrity signal. The SQLite dataset remains the reusable source; edited workbook cells are never treated as receipt facts.

## Output modes

Quiet mode does not mention cache checks, paths, hashes, scan boundaries, or reused row counts. With an explicit `--verbose`, report only concise cache status, reused canonical-order count, incremental boundary, inserted/updated counts, and whether a recent export passed integrity validation. Never expose hashes or identifiers.
