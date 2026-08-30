#!/usr/bin/env python3
"""Create the Food Order Insights workbook from one compact JSON file.

This exporter uses only Python's standard library and the bundled minimal OOXML
writer. It never installs dependencies and never reads Gmail or raw email files.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from minimal_xlsx import Workbook


REQUIRED_SHEETS = (
    "Orders",
    "Items",
    "Data Quality",
)

FORBIDDEN_KEYS = {
    "gmail_message_id",
    "gmail_thread_id",
    "provider_order_id",
    "delivery_address",
    "phone_number",
    "recipient",
    "payment_fragment",
    "tracking_link",
    "raw_email",
    "raw_message",
    "body_text",
}

ORDER_COLUMNS = (
    "order_ref",
    "ordered_at",
    "message_received_at",
    "provider",
    "status",
    "currency",
    "food_subtotal",
    "delivery_fee",
    "discount",
    "total_paid",
)

ITEM_COLUMNS = (
    "order_ref",
    "item_name",
    "quantity",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def load_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("The export input must be one JSON object.")
    if not isinstance(payload.get("orders", []), list):
        raise ValueError("orders must be a list.")
    reject_private_fields(payload)
    return payload


def reject_private_fields(value: Any, location: str = "input") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_KEYS:
                raise ValueError(f"Private field '{key}' is not allowed at {location}.")
            reject_private_fields(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_private_fields(child, f"{location}[{index}]")


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    else:
        text = str(value)
    inspected = text.lstrip(" ")
    if text.startswith(("\t", "\r", "\n")) or (
        inspected and inspected[0] in "=+-@"
    ):
        return "'" + text
    return text


def number(value: Any) -> float | int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return value
    return None


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    return parsed.replace(tzinfo=None)


def formats(workbook: Workbook) -> dict[str, Any]:
    return {
        "header": workbook.add_format(
            {
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#315E7D",
                "border": 1,
                "text_wrap": True,
                "valign": "top",
            }
        ),
        "text": workbook.add_format({"valign": "top", "text_wrap": True}),
        "date": workbook.add_format({"num_format": "yyyy-mm-dd hh:mm", "valign": "top"}),
        "money": workbook.add_format({"num_format": "#,##0.00", "valign": "top"}),
        "number": workbook.add_format({"num_format": "0.00", "valign": "top"}),
    }


def write_value(
    sheet: Any,
    row: int,
    col: int,
    value: Any,
    fmts: dict[str, Any],
    kind: str | None = None,
) -> None:
    if value is None or value == "":
        sheet.write_blank(row, col, None)
        return
    if kind == "date":
        parsed = parse_datetime(value)
        if parsed:
            sheet.write_datetime(row, col, parsed, fmts["date"])
            return
    numeric = number(value)
    if numeric is not None:
        selected = fmts.get(kind or "number", fmts["number"])
        sheet.write_number(row, col, numeric, selected)
        return
    sheet.write_string(row, col, safe_text(value), fmts["text"])


def finish_table_sheet(sheet: Any, row_count: int, col_count: int) -> None:
    sheet.freeze_panes(1, 0)
    if row_count:
        sheet.autofilter(0, 0, row_count, col_count - 1)
    sheet.set_column(0, col_count - 1, 16)
    sheet.set_column(0, 0, 13)


def normalize_orders(payload: dict[str, Any]) -> list[dict[str, Any]]:
    orders: list[dict[str, Any]] = []
    for index, raw in enumerate(payload.get("orders", []), start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"orders[{index - 1}] must be an object.")
        order = dict(raw)
        order["order_ref"] = safe_text(order.get("order_ref") or f"order-{index:04d}")
        orders.append(order)
    return orders


def write_orders(
    workbook: Workbook,
    orders: list[dict[str, Any]],
    fmts: dict[str, Any],
) -> None:
    sheet = workbook.add_worksheet("Orders")
    for col, header in enumerate(ORDER_COLUMNS):
        sheet.write(0, col, header, fmts["header"])
    for row_index, order in enumerate(orders, start=1):
        for col, key in enumerate(ORDER_COLUMNS):
            value = order.get(key)
            if key in {"ordered_at", "message_received_at"}:
                write_value(sheet, row_index, col, value, fmts, "date")
            elif key in {
                "food_subtotal",
                "delivery_fee",
                "discount",
                "total_paid",
            }:
                write_value(sheet, row_index, col, value, fmts, "money")
            else:
                write_value(sheet, row_index, col, value, fmts)
    finish_table_sheet(sheet, len(orders), len(ORDER_COLUMNS))
    sheet.set_column(1, 2, 19)
    sheet.set_column(3, 5, 18)


def flatten_items(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for order in orders:
        for item in order.get("items", []) or []:
            if not isinstance(item, dict):
                continue
            base = {
                "order_ref": order["order_ref"],
                "item_name": item.get("item_name", item.get("raw_name")),
                "quantity": item.get("quantity"),
            }
            rows.append(base)
    return rows


def write_items(
    workbook: Workbook,
    orders: list[dict[str, Any]],
    fmts: dict[str, Any],
) -> None:
    rows = flatten_items(orders)
    sheet = workbook.add_worksheet("Items")
    for col, header in enumerate(ITEM_COLUMNS):
        sheet.write(0, col, header, fmts["header"])
    for row_index, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        for col, key in enumerate(ITEM_COLUMNS):
            value = item.get(key)
            if key == "quantity":
                write_value(sheet, row_index, col, value, fmts, "number")
            else:
                write_value(sheet, row_index, col, value, fmts)
    finish_table_sheet(sheet, len(rows), len(ITEM_COLUMNS))
    sheet.set_column(1, 1, 28)


def write_data_quality(
    workbook: Workbook,
    payload: dict[str, Any],
    orders: list[dict[str, Any]],
    fmts: dict[str, Any],
) -> None:
    supplied = payload.get("data_quality", {})
    rows: list[tuple[str, Any, str]] = [
        ("canonical_orders", len(orders), "Computed from export input"),
        (
            "orders_with_total",
            sum(number(order.get("total_paid")) is not None for order in orders),
            "Computed from Orders",
        ),
    ]
    confidence_values = [
        float(value)
        for order in orders
        if (value := number(order.get("parse_confidence"))) is not None
    ]
    if confidence_values:
        rows.append(
            (
                "low_confidence_orders",
                sum(value < 0.75 for value in confidence_values),
                f"parse_confidence < 0.75; available for {len(confidence_values)}/{len(orders)} orders",
            )
        )
    if isinstance(supplied, dict):
        rows.extend((safe_text(key), value, "Supplied by completed mailbox scan") for key, value in supplied.items())
    sheet = workbook.add_worksheet("Data Quality")
    for col, header in enumerate(("metric", "value", "basis")):
        sheet.write(0, col, header, fmts["header"])
    for row_index, (metric, value, basis) in enumerate(rows, start=1):
        write_value(sheet, row_index, 0, metric, fmts)
        write_value(sheet, row_index, 1, value, fmts)
        write_value(sheet, row_index, 2, basis, fmts)
    finish_table_sheet(sheet, len(rows), 3)
    sheet.set_column(0, 0, 28)
    sheet.set_column(2, 2, 42)


def build_workbook(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook(
        output,
        {
            "constant_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
            "strings_to_numbers": False,
        },
    )
    workbook.set_properties(
        {
            "title": "Food Order Insights",
            "subject": "Personal food-order analysis",
            "comments": "Generated from normalized receipt data; raw emails are not included.",
        }
    )
    fmts = formats(workbook)
    orders = normalize_orders(payload)
    write_orders(workbook, orders, fmts)
    write_items(workbook, orders, fmts)
    write_data_quality(workbook, payload, orders, fmts)
    workbook.close()


def verify_workbook(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Workbook was not created.")
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"Workbook archive is corrupt at {bad_member}.")
        workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
        for sheet in REQUIRED_SHEETS:
            if f'name="{sheet}"' not in workbook_xml:
                raise ValueError(f"Workbook is missing the '{sheet}' sheet.")


def main() -> int:
    args = parse_args()
    try:
        payload = load_payload(args.input)
        build_workbook(payload, args.output)
        verify_workbook(args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return 1
    resolved_output = str(args.output.resolve())
    if args.verbose:
        print(
            json.dumps(
                {
                    "mode": "verbose",
                    "output": resolved_output,
                    "writer": "stdlib-ooxml",
                    "third_party_dependencies": 0,
                    "canonical_orders": len(payload.get("orders", [])),
                    "sheet_count": len(REQUIRED_SHEETS),
                    "sheets": list(REQUIRED_SHEETS),
                    "archive_verified": True,
                    "private_field_guard": True,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    else:
        print(resolved_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
