#!/usr/bin/env python3
"""Local, privacy-minimized incremental cache for Food Order Insights."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1"
DEFAULT_DB = Path.home() / ".codex" / "food-order-insights" / "orders.sqlite3"
RAW_CONTENT_KEYS = {
    "body_text",
    "raw_email",
    "raw_message",
    "html_body",
    "delivery_address",
    "phone_number",
    "recipient",
    "payment_fragment",
    "tracking_link",
    "customer_note",
    "customer_notes",
    "order_note",
    "order_notes",
}

EXPORT_META_KEYS = (
    "export_path",
    "export_created_at",
    "export_sha256",
    "export_mtime_ns",
    "export_size",
)

ORDER_FIELDS = (
    "ordered_at",
    "message_received_at",
    "analysis_time_basis",
    "provider",
    "restaurant",
    "status",
    "currency",
    "food_subtotal",
    "delivery_fee",
    "service_fee",
    "small_order_fee",
    "tip",
    "discount",
    "refund_amount",
    "total_paid",
    "estimated_calories_low",
    "estimated_calories_high",
    "calorie_confidence",
    "parse_confidence",
)

ITEM_FIELDS = (
    "raw_name",
    "quantity",
    "unit_price",
    "line_total",
    "variant",
    "extras",
    "estimated_calories_low",
    "estimated_calories_high",
    "calorie_confidence",
    "balance_category",
    "matched_phrase",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status")
    status.add_argument("--account-scope")
    status.add_argument("--scope-start")
    status.add_argument("--recent-days", type=int, default=30)

    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("--input", type=Path, required=True)

    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--from", dest="date_from")
    snapshot.add_argument("--to", dest="date_to")
    snapshot.add_argument("--output", type=Path)

    export_payload = subparsers.add_parser("export-payload")
    export_payload.add_argument("--from", dest="date_from")
    export_payload.add_argument("--to", dest="date_to")
    export_payload.add_argument("--output", type=Path, required=True)

    register = subparsers.add_parser("register-export")
    register.add_argument("--path", type=Path, required=True)
    return parser.parse_args()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime | None = None) -> str:
    return (value or utc_now()).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def ensure_no_raw_content(value: Any, location: str = "input") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in RAW_CONTENT_KEYS:
                raise ValueError(f"Field '{key}' is not permitted in the local cache at {location}.")
            ensure_no_raw_content(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            ensure_no_raw_content(child, f"{location}[{index}]")


def number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def connect(path: Path, create: bool = True) -> sqlite3.Connection:
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.parent.chmod(0o700)
        except OSError:
            pass
        connection = sqlite3.connect(path)
    else:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    if create:
        initialize(connection)
        try:
            path.chmod(0o600)
        except OSError:
            pass
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            cache_key TEXT PRIMARY KEY,
            provider_order_key TEXT,
            thread_key TEXT,
            ordered_at TEXT,
            message_received_at TEXT,
            analysis_time_basis TEXT,
            provider TEXT,
            restaurant TEXT,
            status TEXT,
            currency TEXT,
            food_subtotal REAL,
            delivery_fee REAL,
            service_fee REAL,
            small_order_fee REAL,
            tip REAL,
            discount REAL,
            refund_amount REAL,
            total_paid REAL,
            estimated_calories_low REAL,
            estimated_calories_high REAL,
            calorie_confidence TEXT,
            parse_confidence REAL
        );
        CREATE INDEX IF NOT EXISTS orders_ordered_at ON orders(ordered_at);
        CREATE INDEX IF NOT EXISTS orders_provider_order_key ON orders(provider_order_key);
        CREATE INDEX IF NOT EXISTS orders_thread_key ON orders(thread_key);
        CREATE TABLE IF NOT EXISTS items (
            order_key TEXT NOT NULL,
            item_index INTEGER NOT NULL,
            raw_name TEXT,
            quantity REAL,
            unit_price REAL,
            line_total REAL,
            variant TEXT,
            extras_json TEXT,
            estimated_calories_low REAL,
            estimated_calories_high REAL,
            calorie_confidence TEXT,
            balance_category TEXT,
            matched_phrase TEXT,
            PRIMARY KEY(order_key, item_index),
            FOREIGN KEY(order_key) REFERENCES orders(cache_key) ON DELETE CASCADE
        );
        """
    )
    set_meta(connection, "schema_version", SCHEMA_VERSION)
    if get_meta(connection, "salt") is None:
        set_meta(connection, "salt", secrets.token_hex(32))
    connection.commit()


def get_meta(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return str(row[0]) if row else None


def set_meta(connection: sqlite3.Connection, key: str, value: Any) -> None:
    connection.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


def digest(connection: sqlite3.Connection, kind: str, value: Any) -> str | None:
    if value is None or str(value) == "":
        return None
    salt = bytes.fromhex(get_meta(connection, "salt") or "")
    payload = f"{kind}:{value}".encode("utf-8", "replace")
    return hashlib.sha256(salt + payload).hexdigest()


def content_fingerprint(order: dict[str, Any]) -> str:
    item_names = []
    for item in order.get("items", []) or []:
        if isinstance(item, dict):
            item_names.append(item.get("raw_name") or item.get("item_name"))
    payload = {
        "provider": order.get("provider"),
        "ordered_at": order.get("ordered_at") or order.get("message_received_at"),
        "restaurant": order.get("restaurant") or order.get("restaurant_name"),
        "total_paid": order.get("total_paid"),
        "items": item_names,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def order_keys(connection: sqlite3.Connection, order: dict[str, Any]) -> tuple[str, str | None, str | None]:
    provider_order_key = digest(connection, "provider_order", order.get("provider_order_id"))
    thread_key = digest(connection, "thread", order.get("gmail_thread_id"))
    message_key = digest(connection, "message", order.get("gmail_message_id"))
    candidates: set[str] = set()
    if provider_order_key:
        candidates.update(
            str(row[0])
            for row in connection.execute(
                "SELECT cache_key FROM orders WHERE provider_order_key = ?", (provider_order_key,)
            )
        )
    if thread_key:
        candidates.update(
            str(row[0])
            for row in connection.execute(
                "SELECT cache_key FROM orders WHERE thread_key = ?", (thread_key,)
            )
        )
    if len(candidates) > 1:
        raise ValueError("Incoming identifiers match more than one cached order.")
    cache_key = next(iter(candidates), None) or provider_order_key or thread_key or message_key
    if cache_key is None:
        cache_key = digest(connection, "content", content_fingerprint(order))
    if cache_key is None:
        raise ValueError("Unable to derive a cache key for an order.")
    return cache_key, provider_order_key, thread_key


def merge_boundary(current: str | None, incoming: str | None, earliest: bool) -> str | None:
    if not current:
        return incoming
    if not incoming:
        return current
    current_time = parse_time(current)
    incoming_time = parse_time(incoming)
    if not current_time or not incoming_time:
        return min(current, incoming) if earliest else max(current, incoming)
    chosen = min(current_time, incoming_time) if earliest else max(current_time, incoming_time)
    return iso_utc(chosen)


def ingest(path: Path, input_path: Path) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("orders", []), list):
        raise ValueError("Cache input must be an object containing an orders list.")
    ensure_no_raw_content(payload)
    scan = payload.get("scan", {}) if isinstance(payload.get("scan"), dict) else {}
    connection = connect(path)
    try:
        full_rescan = scan.get("full_rescan") is True
        scan_complete = scan.get("complete") is True
        coverage_start = scan.get("coverage_start")
        coverage_end = scan.get("coverage_end")
        checkpoint_at = scan.get("checkpoint_at") or scan.get("completed_at") or iso_utc()
        parsed_start = parse_time(coverage_start)
        parsed_end = parse_time(coverage_end)
        if scan_complete and (
            not parse_time(checkpoint_at)
            or not parsed_start
            or not parsed_end
            or parsed_start > parsed_end
        ):
            raise ValueError(
                "A complete scan requires valid checkpoint_at, coverage_start, and coverage_end values."
            )
        account_scope = scan.get("account_scope", "default")
        account_hash = digest(connection, "account", account_scope)
        stored_account = get_meta(connection, "account_hash")
        if stored_account and stored_account != account_hash:
            if not (full_rescan and scan_complete):
                raise ValueError("Cache belongs to a different Gmail account scope.")
            connection.execute("DELETE FROM orders")
            connection.execute(
                "DELETE FROM meta WHERE key NOT IN ('schema_version', 'salt')"
            )
        set_meta(connection, "account_hash", account_hash)

        if full_rescan and scan_complete:
            if not parsed_start or not parsed_end or parsed_start > parsed_end:
                raise ValueError("A full rescan requires valid coverage_start and coverage_end values.")
            connection.execute(
                "DELETE FROM orders "
                "WHERE datetime(COALESCE(message_received_at, ordered_at)) >= datetime(?) "
                "AND datetime(COALESCE(message_received_at, ordered_at)) <= datetime(?)",
                (coverage_start, coverage_end),
            )

        inserted = 0
        updated = 0
        for raw_order in payload.get("orders", []):
            if not isinstance(raw_order, dict):
                continue
            order = dict(raw_order)
            if not order.get("restaurant") and order.get("restaurant_name"):
                order["restaurant"] = order.get("restaurant_name")
            cache_key, provider_order_key, thread_key = order_keys(connection, order)
            existed = connection.execute(
                "SELECT 1 FROM orders WHERE cache_key = ?", (cache_key,)
            ).fetchone() is not None
            values = [
                cache_key,
                provider_order_key,
                thread_key,
                order.get("ordered_at"),
                order.get("message_received_at"),
                order.get("analysis_time_basis"),
                order.get("provider"),
                order.get("restaurant"),
                order.get("status"),
                order.get("currency"),
                number(order.get("food_subtotal")),
                number(order.get("delivery_fee")),
                number(order.get("service_fee")),
                number(order.get("small_order_fee")),
                number(order.get("tip")),
                number(order.get("discount")),
                number(order.get("refund_amount")),
                number(order.get("total_paid")),
                number(order.get("estimated_calories_low")),
                number(order.get("estimated_calories_high")),
                order.get("calorie_confidence"),
                number(order.get("parse_confidence")),
            ]
            columns = (
                "cache_key,provider_order_key,thread_key,ordered_at,message_received_at,"
                "analysis_time_basis,provider,restaurant,status,currency,food_subtotal,"
                "delivery_fee,service_fee,small_order_fee,tip,discount,refund_amount,"
                "total_paid,estimated_calories_low,estimated_calories_high,"
                "calorie_confidence,parse_confidence"
            )
            updates = ",".join(
                f"{field}=COALESCE(excluded.{field},orders.{field})"
                for field in (
                    "provider_order_key",
                    "thread_key",
                    *ORDER_FIELDS,
                )
            )
            connection.execute(
                f"INSERT INTO orders({columns}) VALUES({','.join('?' for _ in values)}) "
                f"ON CONFLICT(cache_key) DO UPDATE SET {updates}",
                values,
            )

            items = order.get("items", [])
            if isinstance(items, list) and items:
                connection.execute("DELETE FROM items WHERE order_key = ?", (cache_key,))
                for index, item in enumerate(items):
                    if not isinstance(item, dict):
                        continue
                    connection.execute(
                        "INSERT INTO items(order_key,item_index,raw_name,quantity,unit_price,"
                        "line_total,variant,extras_json,estimated_calories_low,"
                        "estimated_calories_high,calorie_confidence,balance_category,matched_phrase) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            cache_key,
                            index,
                            item.get("raw_name") or item.get("item_name"),
                            number(item.get("quantity")),
                            number(item.get("unit_price")),
                            number(item.get("line_total")),
                            item.get("variant"),
                            json.dumps(item.get("extras", []), ensure_ascii=False, separators=(",", ":")),
                            number(item.get("estimated_calories_low")),
                            number(item.get("estimated_calories_high")),
                            item.get("calorie_confidence"),
                            item.get("balance_category"),
                            item.get("matched_phrase"),
                        ),
                    )
            if existed:
                updated += 1
            else:
                inserted += 1

        if scan_complete:
            set_meta(connection, "last_complete_scan_at", checkpoint_at)
            coverage_start = merge_boundary(
                get_meta(connection, "coverage_start"), scan.get("coverage_start"), True
            )
            coverage_end = merge_boundary(
                get_meta(connection, "coverage_end"), scan.get("coverage_end"), False
            )
            if coverage_start:
                set_meta(connection, "coverage_start", coverage_start)
            if coverage_end:
                set_meta(connection, "coverage_end", coverage_end)
            if full_rescan:
                connection.executemany(
                    "DELETE FROM meta WHERE key = ?", ((key,) for key in EXPORT_META_KEYS)
                )
        set_meta(connection, "dataset_updated_at", iso_utc())
        connection.commit()
        total = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        return {
            "status": "ok",
            "inserted_orders": inserted,
            "updated_orders": updated,
            "cached_orders": total,
            "scan_checkpoint_advanced": scan_complete,
        }
    finally:
        connection.close()


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def cache_status(
    path: Path,
    account_scope: str | None,
    scope_start: str | None,
    recent_days: int,
) -> dict[str, Any]:
    if not path.is_file():
        return {"usable": False, "reason": "cache_missing", "db": str(path)}
    try:
        connection = connect(path, create=False)
    except sqlite3.Error:
        return {"usable": False, "reason": "cache_unreadable", "db": str(path)}
    try:
        integrity_row = connection.execute("PRAGMA integrity_check").fetchone()
        integrity = integrity_row[0] if integrity_row else "missing"
        if integrity != "ok":
            return {"usable": False, "reason": "cache_integrity_failed", "detail": integrity}
        meta = {row["key"]: row["value"] for row in connection.execute("SELECT key,value FROM meta")}
        if meta.get("schema_version") != SCHEMA_VERSION or not meta.get("salt"):
            return {"usable": False, "reason": "cache_schema_mismatch"}
        if not meta.get("last_complete_scan_at"):
            return {"usable": False, "reason": "cache_has_no_complete_scan"}
        last_scan = parse_time(meta.get("last_complete_scan_at"))
        if not last_scan:
            return {"usable": False, "reason": "cache_has_no_complete_scan"}
        if account_scope is not None:
            candidate = digest(connection, "account", account_scope)
            if candidate != meta.get("account_hash"):
                return {"usable": False, "reason": "account_scope_mismatch"}

        if scope_start and not parse_time(scope_start):
            return {"usable": False, "reason": "requested_scope_invalid"}
        if scope_start and not meta.get("coverage_start"):
            return {"usable": False, "reason": "cache_coverage_unknown"}
        if scope_start and meta.get("coverage_start"):
            requested = parse_time(scope_start)
            covered = parse_time(meta.get("coverage_start"))
            if requested and covered and requested < covered:
                return {
                    "usable": False,
                    "reason": "requested_scope_starts_before_cache",
                    "coverage_start": meta.get("coverage_start"),
                }

        export_state = "none"
        created = parse_time(meta.get("export_created_at"))
        if created and utc_now() - created <= timedelta(days=max(0, recent_days)):
            export_path = Path(meta.get("export_path", ""))
            export_state = "unchanged"
            if not export_path.is_file():
                export_state = "missing"
            else:
                stat = export_path.stat()
                if (
                    str(stat.st_mtime_ns) != meta.get("export_mtime_ns")
                    or str(stat.st_size) != meta.get("export_size")
                    or file_sha256(export_path) != meta.get("export_sha256")
                ):
                    export_state = "modified"
            if export_state != "unchanged":
                return {
                    "usable": False,
                    "reason": f"recent_export_{export_state}",
                    "recent_export_status": export_state,
                }
        elif created:
            export_state = "expired"

        count = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        item_count = connection.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        return {
            "usable": True,
            "reason": "cache_valid",
            "cached_orders": count,
            "cached_items": item_count,
            "coverage_start": meta.get("coverage_start"),
            "coverage_end": meta.get("coverage_end"),
            "last_complete_scan_at": meta.get("last_complete_scan_at"),
            "scan_after_unix": int(last_scan.timestamp()) + 1 if last_scan else None,
            "recent_export_status": export_state,
        }
    except (OSError, ValueError, sqlite3.Error):
        return {"usable": False, "reason": "cache_unreadable", "db": str(path)}
    finally:
        connection.close()


def selected_orders(
    connection: sqlite3.Connection, date_from: str | None, date_to: str | None
) -> list[sqlite3.Row]:
    clauses = []
    values: list[Any] = []
    time_expr = "COALESCE(ordered_at, message_received_at)"
    if date_from:
        clauses.append(f"datetime({time_expr}) >= datetime(?)")
        values.append(date_from)
    if date_to:
        clauses.append(f"datetime({time_expr}) <= datetime(?)")
        values.append(date_to)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return list(connection.execute(f"SELECT * FROM orders{where} ORDER BY {time_expr}", values))


def order_payload(connection: sqlite3.Connection, row: sqlite3.Row, index: int) -> dict[str, Any]:
    order = {field: row[field] for field in ORDER_FIELDS}
    order["order_ref"] = f"order-{index:04d}"
    item_rows = connection.execute(
        "SELECT * FROM items WHERE order_key = ? ORDER BY item_index", (row["cache_key"],)
    )
    items = []
    for item_row in item_rows:
        item = {field: item_row[field] for field in ITEM_FIELDS if field != "extras"}
        item["extras"] = json.loads(item_row["extras_json"] or "[]")
        items.append(item)
    order["items"] = items
    return order


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    try:
        temporary.chmod(0o600)
    except OSError:
        pass
    os.replace(temporary, path)


def snapshot(path: Path, date_from: str | None, date_to: str | None) -> dict[str, Any]:
    connection = connect(path, create=False)
    try:
        rows = selected_orders(connection, date_from, date_to)
        return {
            "orders": [order_payload(connection, row, index) for index, row in enumerate(rows, 1)],
            "cache": {
                "coverage_start": get_meta(connection, "coverage_start"),
                "coverage_end": get_meta(connection, "coverage_end"),
                "last_complete_scan_at": get_meta(connection, "last_complete_scan_at"),
            },
        }
    finally:
        connection.close()


def export_payload(path: Path, date_from: str | None, date_to: str | None) -> dict[str, Any]:
    full = snapshot(path, date_from, date_to)
    orders = []
    for source in full["orders"]:
        orders.append(
            {
                "order_ref": source.get("order_ref"),
                "ordered_at": source.get("ordered_at"),
                "message_received_at": source.get("message_received_at"),
                "provider": source.get("provider"),
                "status": source.get("status"),
                "currency": source.get("currency"),
                "food_subtotal": source.get("food_subtotal"),
                "delivery_fee": source.get("delivery_fee"),
                "discount": source.get("discount"),
                "total_paid": source.get("total_paid"),
                "items": [
                    {
                        "item_name": item.get("raw_name"),
                        "quantity": item.get("quantity"),
                    }
                    for item in source.get("items", [])
                ],
            }
        )
    return {
        "orders": orders,
        "data_quality": {
            "source": "local_incremental_cache",
            "coverage_start": full["cache"].get("coverage_start"),
            "coverage_end": full["cache"].get("coverage_end"),
            "last_complete_scan_at": full["cache"].get("last_complete_scan_at"),
        },
    }


def register_export(path: Path, export_path: Path) -> dict[str, Any]:
    if not export_path.is_file():
        raise ValueError("Export file does not exist.")
    connection = connect(path)
    try:
        resolved = export_path.resolve()
        stat = resolved.stat()
        set_meta(connection, "export_path", resolved)
        set_meta(connection, "export_created_at", iso_utc())
        set_meta(connection, "export_sha256", file_sha256(resolved))
        set_meta(connection, "export_mtime_ns", stat.st_mtime_ns)
        set_meta(connection, "export_size", stat.st_size)
        connection.commit()
        return {"status": "ok", "registered_export": str(resolved)}
    finally:
        connection.close()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "status":
            result = cache_status(args.db, args.account_scope, args.scope_start, args.recent_days)
        elif args.command == "ingest":
            result = ingest(args.db, args.input)
        elif args.command == "snapshot":
            result = snapshot(args.db, args.date_from, args.date_to)
            if args.output:
                write_json(args.output, result)
                result = {"status": "ok", "output": str(args.output.resolve())}
        elif args.command == "export-payload":
            write_json(args.output, export_payload(args.db, args.date_from, args.date_to))
            result = {"status": "ok", "output": str(args.output.resolve())}
        elif args.command == "register-export":
            result = register_export(args.db, args.path)
        else:  # pragma: no cover
            raise ValueError("Unknown command.")
        emit(result)
        return 0
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as exc:
        emit({"status": "error", "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
