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
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from minimal_xlsx import Workbook, xl_rowcol_to_cell


REQUIRED_SHEETS = (
    "Summary",
    "Orders",
    "Items",
    "Period Breakdown",
    "Risk Report",
    "Recommendations",
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
    "net_spend",
    "estimated_calories_low",
    "estimated_calories_high",
    "calorie_confidence",
    "parse_confidence",
    "warnings",
)

ITEM_COLUMNS = (
    "order_ref",
    "item_name",
    "quantity",
    "unit_price",
    "line_total",
    "variant",
    "extra_name",
    "extra_price",
    "estimated_calories_low",
    "estimated_calories_high",
    "calorie_confidence",
    "balance_category",
    "matched_phrase",
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
        "title": workbook.add_format(
            {"bold": True, "font_size": 16, "font_color": "#17324D"}
        ),
        "section": workbook.add_format(
            {"bold": True, "font_color": "#17324D", "bg_color": "#DCEAF7"}
        ),
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
        "percent": workbook.add_format({"num_format": "0.0%", "valign": "top"}),
        "number": workbook.add_format({"num_format": "0.00", "valign": "top"}),
        "integer": workbook.add_format({"num_format": "0", "valign": "top"}),
        "note": workbook.add_format(
            {"font_color": "#555555", "italic": True, "text_wrap": True}
        ),
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
        if not order.get("restaurant") and order.get("restaurant_name"):
            order["restaurant"] = order.get("restaurant_name")
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
            if key == "net_spend":
                total = number(order.get("total_paid"))
                refund = number(order.get("refund_amount")) or 0
                if total is not None:
                    total_cell = xl_rowcol_to_cell(row_index, ORDER_COLUMNS.index("total_paid"))
                    refund_cell = xl_rowcol_to_cell(row_index, ORDER_COLUMNS.index("refund_amount"))
                    formula = f'=IF({total_cell}="","",{total_cell}-IF({refund_cell}="",0,{refund_cell}))'
                    sheet.write_formula(row_index, col, formula, fmts["money"], total - refund)
                else:
                    sheet.write_blank(row_index, col, None)
                continue
            value = order.get(key)
            if key in {"ordered_at", "message_received_at"}:
                write_value(sheet, row_index, col, value, fmts, "date")
            elif key in {
                "food_subtotal",
                "delivery_fee",
                "service_fee",
                "small_order_fee",
                "tip",
                "discount",
                "refund_amount",
                "total_paid",
            }:
                write_value(sheet, row_index, col, value, fmts, "money")
            elif key == "parse_confidence":
                write_value(sheet, row_index, col, value, fmts, "percent")
            else:
                write_value(sheet, row_index, col, value, fmts)
    finish_table_sheet(sheet, len(orders), len(ORDER_COLUMNS))
    sheet.set_column(1, 2, 19)
    sheet.set_column(4, 7, 18)
    sheet.set_column(len(ORDER_COLUMNS) - 1, len(ORDER_COLUMNS) - 1, 42)


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
                "unit_price": item.get("unit_price"),
                "line_total": item.get("line_total"),
                "variant": item.get("variant"),
                "estimated_calories_low": item.get("estimated_calories_low"),
                "estimated_calories_high": item.get("estimated_calories_high"),
                "calorie_confidence": item.get("calorie_confidence"),
                "balance_category": item.get("balance_category"),
                "matched_phrase": item.get("matched_phrase"),
            }
            extras = item.get("extras", []) or []
            if not extras:
                rows.append(base)
            else:
                for extra in extras:
                    row = dict(base)
                    if isinstance(extra, dict):
                        row["extra_name"] = extra.get("name")
                        row["extra_price"] = extra.get("price")
                    else:
                        row["extra_name"] = extra
                    rows.append(row)
    return rows


def write_items(
    workbook: Workbook,
    orders: list[dict[str, Any]],
    payload: dict[str, Any],
    fmts: dict[str, Any],
) -> None:
    provided = payload.get("items")
    rows = provided if isinstance(provided, list) and provided else flatten_items(orders)
    sheet = workbook.add_worksheet("Items")
    for col, header in enumerate(ITEM_COLUMNS):
        sheet.write(0, col, header, fmts["header"])
    for row_index, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        for col, key in enumerate(ITEM_COLUMNS):
            value = item.get(key)
            if key in {"unit_price", "line_total", "extra_price"}:
                write_value(sheet, row_index, col, value, fmts, "money")
            elif key == "quantity":
                write_value(sheet, row_index, col, value, fmts, "number")
            else:
                write_value(sheet, row_index, col, value, fmts)
    finish_table_sheet(sheet, len(rows), len(ITEM_COLUMNS))
    sheet.set_column(1, 1, 28)
    sheet.set_column(5, 6, 22)


def derive_breakdowns(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregates: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "order_count": 0,
            "orders_with_total": 0,
            "gross_spend": 0.0,
            "net_spend": 0.0,
            "delivery_fees": 0.0,
            "service_fees": 0.0,
            "discounts": 0.0,
            "orders_with_calorie_estimate": 0,
            "estimated_calories_low": 0.0,
            "estimated_calories_high": 0.0,
        }
    )
    for order in orders:
        if str(order.get("status", "")).lower() == "cancelled":
            continue
        dt = parse_datetime(order.get("ordered_at") or order.get("message_received_at"))
        if not dt:
            continue
        currency = safe_text(order.get("currency") or "unknown")
        dimensions = {
            "year": f"{dt.year:04d}",
            "month": f"{dt.year:04d}-{dt.month:02d}",
            "iso_week": f"{dt.isocalendar().year:04d}-W{dt.isocalendar().week:02d}",
            "weekday": f"{dt.weekday() + 1}-{dt.strftime('%A')}",
            "hour": f"{dt.hour:02d}:00",
        }
        for breakdown_type, label in dimensions.items():
            row = aggregates[(breakdown_type, label, currency)]
            row["order_count"] += 1
            total = number(order.get("total_paid"))
            if total is not None:
                refund = number(order.get("refund_amount")) or 0
                row["orders_with_total"] += 1
                row["gross_spend"] += total
                row["net_spend"] += total - refund
            for source, target in (
                ("delivery_fee", "delivery_fees"),
                ("service_fee", "service_fees"),
                ("discount", "discounts"),
            ):
                value = number(order.get(source))
                if value is not None:
                    row[target] += value
            low = number(order.get("estimated_calories_low"))
            high = number(order.get("estimated_calories_high"))
            if low is not None and high is not None:
                row["orders_with_calorie_estimate"] += 1
                row["estimated_calories_low"] += low
                row["estimated_calories_high"] += high
    result = []
    for (kind, label, currency), values in sorted(aggregates.items()):
        row = {"breakdown_type": kind, "period": label, "currency": currency}
        row.update(values)
        if not values["orders_with_total"]:
            row["gross_spend"] = None
            row["net_spend"] = None
        if not values["orders_with_calorie_estimate"]:
            row["estimated_calories_low"] = None
            row["estimated_calories_high"] = None
        result.append(row)
    return result


def write_breakdowns(
    workbook: Workbook,
    orders: list[dict[str, Any]],
    fmts: dict[str, Any],
) -> None:
    rows = derive_breakdowns(orders)
    columns = (
        "breakdown_type",
        "period",
        "currency",
        "order_count",
        "orders_with_total",
        "gross_spend",
        "net_spend",
        "delivery_fees",
        "service_fees",
        "discounts",
        "orders_with_calorie_estimate",
        "estimated_calories_low",
        "estimated_calories_high",
    )
    sheet = workbook.add_worksheet("Period Breakdown")
    for col, header in enumerate(columns):
        sheet.write(0, col, header, fmts["header"])
    for row_index, row in enumerate(rows, start=1):
        for col, key in enumerate(columns):
            kind = "money" if key in {
                "gross_spend",
                "net_spend",
                "delivery_fees",
                "service_fees",
                "discounts",
            } else "integer" if key in {
                "order_count",
                "orders_with_total",
                "orders_with_calorie_estimate",
            } else None
            write_value(sheet, row_index, col, row.get(key), fmts, kind)
    finish_table_sheet(sheet, len(rows), len(columns))


def write_summary(
    workbook: Workbook,
    payload: dict[str, Any],
    orders: list[dict[str, Any]],
    fmts: dict[str, Any],
) -> None:
    sheet = workbook.add_worksheet("Summary")
    sheet.write(0, 0, "Food Order Insights", fmts["title"])
    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}
    pairs = (
        ("Requested scope", metadata.get("requested_scope")),
        ("Coverage start", metadata.get("coverage_start")),
        ("Coverage end", metadata.get("coverage_end")),
        ("Generated at", metadata.get("generated_at")),
        ("Timezone", metadata.get("timezone")),
        ("Unique canonical orders", len(orders)),
    )
    row = 2
    for label, value in pairs:
        sheet.write(row, 0, label, fmts["section"])
        write_value(sheet, row, 1, value, fmts)
        row += 1
    row += 1
    sheet.write(row, 0, "Spend by currency", fmts["section"])
    row += 1
    headers = ("Currency", "Orders", "Orders with total", "Gross spend", "Net spend")
    for col, header in enumerate(headers):
        sheet.write(row, col, header, fmts["header"])
    currency_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for order in orders:
        currency_rows[safe_text(order.get("currency") or "unknown")].append(order)
    for currency, grouped in sorted(currency_rows.items()):
        row += 1
        known = [order for order in grouped if number(order.get("total_paid")) is not None]
        gross = sum(float(number(order.get("total_paid")) or 0) for order in known)
        net = sum(
            float(number(order.get("total_paid")) or 0)
            - float(number(order.get("refund_amount")) or 0)
            for order in known
        )
        write_value(sheet, row, 0, currency, fmts)
        write_value(sheet, row, 1, len(grouped), fmts, "integer")
        write_value(sheet, row, 2, len(known), fmts, "integer")
        write_value(sheet, row, 3, gross if known else None, fmts, "money")
        write_value(sheet, row, 4, net if known else None, fmts, "money")
    row += 2
    sheet.write(row, 0, "Key patterns", fmts["section"])
    for pattern in payload.get("key_patterns", []) or []:
        row += 1
        sheet.write(row, 0, "•", fmts["text"])
        sheet.write(row, 1, safe_text(pattern), fmts["text"])
    sheet.set_column(0, 0, 24)
    sheet.set_column(1, 1, 58)
    sheet.set_column(2, 4, 18)
    sheet.freeze_panes(2, 0)


def write_risk_report(
    workbook: Workbook,
    payload: dict[str, Any],
    fmts: dict[str, Any],
) -> None:
    report = payload.get("risk_report", {})
    if not isinstance(report, dict):
        report = {}
    sheet = workbook.add_worksheet("Risk Report")
    sheet.write(0, 0, "Order Pattern Risk Report", fmts["title"])
    sheet.write(2, 0, "Scope", fmts["section"])
    sheet.write(2, 1, safe_text(report.get("scope_limitation", "Not supplied")), fmts["note"])
    headers = (
        "metric",
        "status",
        "value",
        "unit",
        "numerator",
        "denominator",
        "window",
        "coverage",
        "comparison",
        "meaning_and_limit",
    )
    row = 4
    for col, header in enumerate(headers):
        sheet.write(row, col, header, fmts["header"])
    for signal in report.get("available_metrics", []) or []:
        if not isinstance(signal, dict):
            continue
        row += 1
        values = (
            signal.get("metric"),
            "available",
            signal.get("value"),
            signal.get("unit"),
            signal.get("numerator"),
            signal.get("denominator"),
            signal.get("window"),
            signal.get("coverage"),
            signal.get("comparison"),
            signal.get("meaning_and_limit"),
        )
        for col, value in enumerate(values):
            kind = None
            if col == 2 and str(signal.get("unit", "")).lower() in {"share", "percent", "percentage"}:
                kind = "percent"
            write_value(sheet, row, col, value, fmts, kind)
    for omission in report.get("not_derived", []) or []:
        if not isinstance(omission, dict):
            continue
        row += 1
        values = (
            omission.get("metric"),
            "not derived",
            None,
            None,
            omission.get("available_count"),
            omission.get("required_count"),
            omission.get("window"),
            omission.get("coverage"),
            None,
            f"{safe_text(omission.get('reason'))} What would make it available: {safe_text(omission.get('needed'))}",
        )
        for col, value in enumerate(values):
            write_value(sheet, row, col, value, fmts)
    sheet.freeze_panes(5, 0)
    if row > 4:
        sheet.autofilter(4, 0, row, len(headers) - 1)
    sheet.set_column(0, 1, 22)
    sheet.set_column(2, 8, 16)
    sheet.set_column(9, 9, 58)


def write_recommendations(
    workbook: Workbook,
    payload: dict[str, Any],
    fmts: dict[str, Any],
) -> None:
    columns = (
        "type",
        "evidence",
        "suggestion",
        "effort",
        "prep_time",
        "progress_measure",
        "fallback",
        "status",
        "evidence_limit",
    )
    rows = payload.get("recommendations", []) or []
    sheet = workbook.add_worksheet("Recommendations")
    for col, header in enumerate(columns):
        sheet.write(0, col, header, fmts["header"])
    for row_index, recommendation in enumerate(rows, start=1):
        if not isinstance(recommendation, dict):
            continue
        for col, key in enumerate(columns):
            write_value(sheet, row_index, col, recommendation.get(key), fmts)
    finish_table_sheet(sheet, len(rows), len(columns))
    sheet.set_column(1, 2, 38)
    sheet.set_column(5, 8, 28)


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
        (
            "low_confidence_orders",
            sum(
                number(order.get("parse_confidence")) is not None
                and float(number(order.get("parse_confidence")) or 0) < 0.75
                for order in orders
            ),
            "parse_confidence < 0.75",
        ),
    ]
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
    write_summary(workbook, payload, orders, fmts)
    write_orders(workbook, orders, fmts)
    write_items(workbook, orders, payload, fmts)
    write_breakdowns(workbook, orders, fmts)
    write_risk_report(workbook, payload, fmts)
    write_recommendations(workbook, payload, fmts)
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
