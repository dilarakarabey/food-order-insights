"""Small dependency-free XLSX writer for the Food Order Insights exporter.

It implements only the workbook features used by export_workbook.py and writes
standard Office Open XML with Python's standard library.
"""

from __future__ import annotations

import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape, quoteattr


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
CORE_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
EXTENDED_NS = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
VT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"

_ILLEGAL_XML = re.compile(
    "[\x00-\x08\x0B\x0C\x0E-\x1F\uD800-\uDFFF\uFFFE\uFFFF]"
)


def _xml_text(value: Any) -> str:
    return escape(_ILLEGAL_XML.sub("", str(value)))


def _rgb(value: str) -> str:
    cleaned = value.lstrip("#").upper()
    return cleaned if len(cleaned) == 8 else "FF" + cleaned


def _column_name(index: int) -> str:
    if index < 0:
        raise ValueError("Column index must be non-negative.")
    letters = ""
    value = index + 1
    while value:
        value, remainder = divmod(value - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def xl_rowcol_to_cell(row: int, col: int) -> str:
    return f"{_column_name(col)}{row + 1}"


def _excel_datetime(value: datetime) -> float:
    if value.tzinfo is not None:
        value = value.replace(tzinfo=None)
    epoch = datetime(1899, 12, 30)
    delta = value - epoch
    return delta.days + (delta.seconds + delta.microseconds / 1_000_000) / 86_400


@dataclass(frozen=True)
class Format:
    properties: dict[str, Any]
    style_id: int


@dataclass
class Cell:
    kind: str
    value: Any = None
    style_id: int = 0
    formula: str | None = None
    cached: Any = None


class Worksheet:
    def __init__(self, name: str) -> None:
        self.name = name
        self.cells: dict[tuple[int, int], Cell] = {}
        self.column_widths: dict[int, float] = {}
        self.freeze: tuple[int, int] | None = None
        self.filter_range: tuple[int, int, int, int] | None = None

    @staticmethod
    def _style(fmt: Format | None) -> int:
        return fmt.style_id if isinstance(fmt, Format) else 0

    def write(self, row: int, col: int, value: Any, fmt: Format | None = None) -> None:
        if value is None:
            self.write_blank(row, col, None, fmt)
        elif isinstance(value, bool):
            self.cells[(row, col)] = Cell("boolean", value, self._style(fmt))
        elif isinstance(value, (int, float)):
            self.write_number(row, col, value, fmt)
        elif isinstance(value, datetime):
            self.write_datetime(row, col, value, fmt)
        else:
            self.write_string(row, col, str(value), fmt)

    def write_blank(
        self,
        row: int,
        col: int,
        _value: Any = None,
        fmt: Format | None = None,
    ) -> None:
        if fmt is not None:
            self.cells[(row, col)] = Cell("blank", None, self._style(fmt))

    def write_string(
        self, row: int, col: int, value: str, fmt: Format | None = None
    ) -> None:
        self.cells[(row, col)] = Cell("string", value, self._style(fmt))

    def write_number(
        self, row: int, col: int, value: float | int, fmt: Format | None = None
    ) -> None:
        self.cells[(row, col)] = Cell("number", value, self._style(fmt))

    def write_datetime(
        self, row: int, col: int, value: datetime, fmt: Format | None = None
    ) -> None:
        self.cells[(row, col)] = Cell("date", value, self._style(fmt))

    def write_formula(
        self,
        row: int,
        col: int,
        formula: str,
        fmt: Format | None = None,
        value: Any = None,
    ) -> None:
        self.cells[(row, col)] = Cell(
            "formula",
            style_id=self._style(fmt),
            formula=formula,
            cached=value,
        )

    def freeze_panes(self, row: int, col: int) -> None:
        self.freeze = (row, col)

    def autofilter(self, first_row: int, first_col: int, last_row: int, last_col: int) -> None:
        self.filter_range = (first_row, first_col, last_row, last_col)

    def set_column(self, first_col: int, last_col: int, width: float) -> None:
        for col in range(first_col, last_col + 1):
            self.column_widths[col] = width

    def _dimension(self) -> str:
        if not self.cells:
            return "A1"
        max_row = max(row for row, _ in self.cells)
        max_col = max(col for _, col in self.cells)
        return f"A1:{xl_rowcol_to_cell(max_row, max_col)}"

    def _sheet_views_xml(self) -> str:
        if not self.freeze or self.freeze == (0, 0):
            return '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        row, col = self.freeze
        attributes = []
        if col:
            attributes.append(f'xSplit="{col}"')
        if row:
            attributes.append(f'ySplit="{row}"')
        attributes.extend(
            [
                f'topLeftCell="{xl_rowcol_to_cell(row, col)}"',
                'activePane="bottomRight"' if row and col else (
                    'activePane="bottomLeft"' if row else 'activePane="topRight"'
                ),
                'state="frozen"',
            ]
        )
        return (
            '<sheetViews><sheetView workbookViewId="0"><pane '
            + " ".join(attributes)
            + '/></sheetView></sheetViews>'
        )

    def _columns_xml(self) -> str:
        if not self.column_widths:
            return ""
        columns = ["<cols>"]
        for col, width in sorted(self.column_widths.items()):
            columns.append(
                f'<col min="{col + 1}" max="{col + 1}" width="{width}" customWidth="1"/>'
            )
        columns.append("</cols>")
        return "".join(columns)

    @staticmethod
    def _cell_xml(row: int, col: int, cell: Cell) -> str:
        reference = xl_rowcol_to_cell(row, col)
        style = f' s="{cell.style_id}"' if cell.style_id else ""
        if cell.kind == "string":
            raw_value = str(cell.value)[:32767]
            value = _xml_text(raw_value)
            preserve = ' xml:space="preserve"' if raw_value != raw_value.strip() else ""
            return f'<c r="{reference}"{style} t="inlineStr"><is><t{preserve}>{value}</t></is></c>'
        if cell.kind == "number":
            return f'<c r="{reference}"{style}><v>{cell.value}</v></c>'
        if cell.kind == "date":
            return f'<c r="{reference}"{style}><v>{_excel_datetime(cell.value):.12g}</v></c>'
        if cell.kind == "boolean":
            return f'<c r="{reference}"{style} t="b"><v>{1 if cell.value else 0}</v></c>'
        if cell.kind == "formula":
            formula = _xml_text((cell.formula or "").lstrip("="))
            cached = "" if cell.cached is None else _xml_text(cell.cached)
            return f'<c r="{reference}"{style}><f>{formula}</f><v>{cached}</v></c>'
        return f'<c r="{reference}"{style}/>'

    def to_xml(self) -> str:
        rows: dict[int, list[tuple[int, Cell]]] = defaultdict(list)
        for (row, col), cell in self.cells.items():
            rows[row].append((col, cell))
        sheet_data = ["<sheetData>"]
        for row in sorted(rows):
            sheet_data.append(f'<row r="{row + 1}">')
            for col, cell in sorted(rows[row]):
                sheet_data.append(self._cell_xml(row, col, cell))
            sheet_data.append("</row>")
        sheet_data.append("</sheetData>")
        filter_xml = ""
        if self.filter_range:
            first_row, first_col, last_row, last_col = self.filter_range
            reference = (
                f"{xl_rowcol_to_cell(first_row, first_col)}:"
                f"{xl_rowcol_to_cell(last_row, last_col)}"
            )
            filter_xml = f'<autoFilter ref="{reference}"/>'
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<worksheet xmlns="{MAIN_NS}" xmlns:r="{REL_NS}">'
            f'<dimension ref="{self._dimension()}"/>'
            f'{self._sheet_views_xml()}'
            '<sheetFormatPr defaultRowHeight="15"/>'
            f'{self._columns_xml()}'
            f'{"".join(sheet_data)}'
            f'{filter_xml}'
            '</worksheet>'
        )


class Workbook:
    def __init__(self, path: str | Path, _options: dict[str, Any] | None = None) -> None:
        self.path = Path(path)
        self.sheets: list[Worksheet] = []
        self.formats: list[Format] = []
        self.properties: dict[str, Any] = {}

    def add_format(self, properties: dict[str, Any] | None = None) -> Format:
        fmt = Format(dict(properties or {}), len(self.formats) + 1)
        self.formats.append(fmt)
        return fmt

    def add_worksheet(self, name: str) -> Worksheet:
        if not name or len(name) > 31 or any(char in name for char in "[]:*?/\\"):
            raise ValueError(f"Invalid worksheet name: {name!r}")
        if name.lower() in {sheet.name.lower() for sheet in self.sheets}:
            raise ValueError(f"Duplicate worksheet name: {name}")
        sheet = Worksheet(name)
        self.sheets.append(sheet)
        return sheet

    def set_properties(self, properties: dict[str, Any]) -> None:
        self.properties = dict(properties)

    def _style_components(
        self,
    ) -> tuple[
        list[dict[str, Any]],
        list[str],
        list[dict[str, Any]],
        list[int],
        list[tuple[str, str]],
    ]:
        fonts: list[dict[str, Any]] = [{}]
        fills = ["none", "gray125"]
        borders = [0]
        num_formats: list[tuple[str, str]] = []
        num_ids: dict[str, int] = {}
        style_records: list[dict[str, Any]] = []

        for fmt in self.formats:
            props = fmt.properties
            font_props = {
                key: props[key]
                for key in ("bold", "italic", "font_size", "font_color")
                if key in props
            }
            if font_props and font_props not in fonts:
                fonts.append(font_props)
            font_id = fonts.index(font_props) if font_props else 0

            fill_id = 0
            background = props.get("bg_color")
            if background:
                marker = str(background)
                if marker not in fills:
                    fills.append(marker)
                fill_id = fills.index(marker)

            border_id = 0
            if props.get("border"):
                if 1 not in borders:
                    borders.append(1)
                border_id = borders.index(1)

            num_fmt_id = 0
            number_format = props.get("num_format")
            if number_format:
                number_format = str(number_format)
                if number_format not in num_ids:
                    num_id = 164 + len(num_ids)
                    num_ids[number_format] = num_id
                    num_formats.append((str(num_id), number_format))
                num_fmt_id = num_ids[number_format]

            style_records.append(
                {
                    "font_id": font_id,
                    "fill_id": fill_id,
                    "border_id": border_id,
                    "num_fmt_id": num_fmt_id,
                    "wrap": bool(props.get("text_wrap")),
                    "vertical": props.get("valign"),
                }
            )
        return style_records, fills, fonts, borders, num_formats

    def _styles_xml(self) -> str:
        records, fills, fonts, borders, num_formats = self._style_components()
        parts = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            f'<styleSheet xmlns="{MAIN_NS}">',
        ]
        if num_formats:
            parts.append(f'<numFmts count="{len(num_formats)}">')
            for num_id, code in num_formats:
                parts.append(f'<numFmt numFmtId="{num_id}" formatCode={quoteattr(code)}/>')
            parts.append("</numFmts>")

        parts.append(f'<fonts count="{len(fonts)}">')
        for font in fonts:
            parts.append("<font>")
            if font.get("bold"):
                parts.append("<b/>")
            if font.get("italic"):
                parts.append("<i/>")
            if font.get("font_size"):
                parts.append(f'<sz val="{font["font_size"]}"/>')
            else:
                parts.append('<sz val="11"/>')
            if font.get("font_color"):
                parts.append(f'<color rgb="{_rgb(str(font["font_color"]))}"/>')
            else:
                parts.append('<color theme="1"/>')
            parts.append('<name val="Calibri"/><family val="2"/><scheme val="minor"/></font>')
        parts.append("</fonts>")

        parts.append(f'<fills count="{len(fills)}">')
        for fill in fills:
            if fill == "none":
                parts.append('<fill><patternFill patternType="none"/></fill>')
            elif fill == "gray125":
                parts.append('<fill><patternFill patternType="gray125"/></fill>')
            else:
                parts.append(
                    f'<fill><patternFill patternType="solid"><fgColor rgb="{_rgb(fill)}"/>'
                    '<bgColor indexed="64"/></patternFill></fill>'
                )
        parts.append("</fills>")

        parts.append(f'<borders count="{len(borders)}">')
        for border in borders:
            if not border:
                parts.append('<border><left/><right/><top/><bottom/><diagonal/></border>')
            else:
                parts.append(
                    '<border><left style="thin"><color auto="1"/></left>'
                    '<right style="thin"><color auto="1"/></right>'
                    '<top style="thin"><color auto="1"/></top>'
                    '<bottom style="thin"><color auto="1"/></bottom><diagonal/></border>'
                )
        parts.append("</borders>")
        parts.append('<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>')
        parts.append(f'<cellXfs count="{len(records) + 1}">')
        parts.append('<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>')
        for record in records:
            attributes = (
                f'numFmtId="{record["num_fmt_id"]}" fontId="{record["font_id"]}" '
                f'fillId="{record["fill_id"]}" borderId="{record["border_id"]}" xfId="0"'
            )
            applications = []
            if record["num_fmt_id"]:
                applications.append('applyNumberFormat="1"')
            if record["font_id"]:
                applications.append('applyFont="1"')
            if record["fill_id"]:
                applications.append('applyFill="1"')
            if record["border_id"]:
                applications.append('applyBorder="1"')
            if record["wrap"] or record["vertical"]:
                applications.append('applyAlignment="1"')
                alignment = []
                if record["wrap"]:
                    alignment.append('wrapText="1"')
                if record["vertical"]:
                    alignment.append(f'vertical={quoteattr(str(record["vertical"]))}')
                parts.append(f'<xf {attributes} {" ".join(applications)}><alignment {" ".join(alignment)}/></xf>')
            else:
                extra = " " + " ".join(applications) if applications else ""
                parts.append(f'<xf {attributes}{extra}/>' )
        parts.append("</cellXfs>")
        parts.append('<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>')
        parts.append('<dxfs count="0"/><tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/>')
        parts.append("</styleSheet>")
        return "".join(parts)

    def _workbook_xml(self) -> str:
        sheets = "".join(
            f'<sheet name={quoteattr(sheet.name)} sheetId="{index}" r:id="rId{index}"/>'
            for index, sheet in enumerate(self.sheets, start=1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<workbook xmlns="{MAIN_NS}" xmlns:r="{REL_NS}">'
            '<fileVersion appName="xl"/><workbookPr/>'
            '<bookViews><workbookView xWindow="0" yWindow="0" windowWidth="24000" windowHeight="12000"/></bookViews>'
            f'<sheets>{sheets}</sheets>'
            '<calcPr calcId="191029" fullCalcOnLoad="1" forceFullCalc="1"/>'
            '</workbook>'
        )

    def _workbook_rels_xml(self) -> str:
        relationships = []
        for index, _sheet in enumerate(self.sheets, start=1):
            relationships.append(
                f'<Relationship Id="rId{index}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                f'Target="worksheets/sheet{index}.xml"/>'
            )
        style_id = len(self.sheets) + 1
        relationships.append(
            f'<Relationship Id="rId{style_id}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
            'Target="styles.xml"/>'
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{PACKAGE_REL_NS}">{"".join(relationships)}</Relationships>'
        )

    def _content_types_xml(self) -> str:
        overrides = [
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
        ]
        overrides.extend(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for index, _sheet in enumerate(self.sheets, start=1)
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Types xmlns="{CONTENT_TYPES_NS}">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'{"".join(overrides)}</Types>'
        )

    @staticmethod
    def _root_rels_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{PACKAGE_REL_NS}">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>'
        )

    def _core_xml(self) -> str:
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        title = _xml_text(self.properties.get("title", "Food Order Insights"))
        subject = _xml_text(self.properties.get("subject", "Personal food-order analysis"))
        description = _xml_text(self.properties.get("comments", ""))
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<cp:coreProperties xmlns:cp="{CORE_NS}" xmlns:dc="{DC_NS}" '
            f'xmlns:dcterms="{DCTERMS_NS}" xmlns:xsi="{XSI_NS}">'
            f'<dc:title>{title}</dc:title><dc:subject>{subject}</dc:subject>'
            '<dc:creator>Food Order Insights</dc:creator><cp:lastModifiedBy>Food Order Insights</cp:lastModifiedBy>'
            f'<dc:description>{description}</dc:description>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
            '</cp:coreProperties>'
        )

    def _app_xml(self) -> str:
        titles = "".join(f'<vt:lpstr>{_xml_text(sheet.name)}</vt:lpstr>' for sheet in self.sheets)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Properties xmlns="{EXTENDED_NS}" xmlns:vt="{VT_NS}">'
            '<Application>Food Order Insights</Application>'
            f'<TitlesOfParts><vt:vector size="{len(self.sheets)}" baseType="lpstr">{titles}</vt:vector></TitlesOfParts>'
            '</Properties>'
        )

    def close(self) -> None:
        if not self.sheets:
            raise ValueError("Workbook must contain at least one worksheet.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", self._content_types_xml())
            archive.writestr("_rels/.rels", self._root_rels_xml())
            archive.writestr("docProps/core.xml", self._core_xml())
            archive.writestr("docProps/app.xml", self._app_xml())
            archive.writestr("xl/workbook.xml", self._workbook_xml())
            archive.writestr("xl/_rels/workbook.xml.rels", self._workbook_rels_xml())
            archive.writestr("xl/styles.xml", self._styles_xml())
            for index, sheet in enumerate(self.sheets, start=1):
                archive.writestr(f"xl/worksheets/sheet{index}.xml", sheet.to_xml())
