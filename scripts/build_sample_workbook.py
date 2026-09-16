"""Generate the customer-facing upload template and the CSV/TXT samples.

The workbook this writes is the canonical template a customer downloads from
Data Studio, so it is generated from the importer's own column names rather
than typed out by hand -- if a required column is ever renamed, this script
stops matching and the mismatch shows up here instead of in a customer's
failed upload.

Run it after changing any dataset's columns:

    .venv/Scripts/python scripts/build_sample_workbook.py

It writes into ui/frontend/public/samples/, which the frontend serves.
"""

from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ui.backend import data_import_service as importer  # noqa: E402
from ui.backend import sample_rows  # noqa: E402

SAMPLES_DIR = REPO_ROOT / "ui" / "frontend" / "public" / "samples"

# The palette is the product's, kept in step with ui/frontend/src/styles/tokens.css.
INDIGO = "4B3B82"
INDIGO_DEEP = "17142F"
GOLD = "CBA85B"
PEARL = "F8F7FB"
LINE = "E2DEEA"

TITLE_FONT = Font(name="Calibri", size=14, bold=True, color=INDIGO_DEEP)
NOTE_FONT = Font(name="Calibri", size=10, color="6E6A78")
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor=INDIGO)
REQUIRED_FILL = PatternFill("solid", fgColor=GOLD)
THIN = Side(style="thin", color=LINE)
CELL_BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


# The rows and column names come from ui/backend/sample_rows.py, which the
# dashboard's "Load sample data" button also uses. Defining them in one place
# is what makes "click the button, then upload this file" report every row as
# unchanged instead of as an edit.
SHEETS = [
    {
        "title": "Daily Operations",
        "dataset": "daily",
        "blurb": (
            "One row per outlet per business date. Cost percentages are against that "
            "outlet's whole day, delivery included. Leave delivery_sales blank if the "
            "outlet does not deliver. Reuse a date and outlet to load a correction; "
            "the previous version is kept, not overwritten."
        ),
        "columns": sample_rows.DAILY_COLUMNS,
        "required": (
            "date", "outlet", "dine_in_sales", "covers", "food_cost_pct",
            "labour_cost_pct", "checklist_total", "checklist_signed_off",
        ),
        "rows": sample_rows.DAILY_ROWS,
    },
    {
        "title": "Events",
        "dataset": "events",
        "blurb": (
            "One row per private dining or event booking. Net and margin are computed "
            "from revenue and costs on load, so there is no margin column here."
        ),
        "columns": sample_rows.EVENT_COLUMNS,
        "required": ("event_id", "event_name", "segment", "date", "covers", "revenue", "food_cost"),
        "rows": sample_rows.EVENT_ROWS,
        "note": "segment must be one of: " + ", ".join(importer.EVENT_SEGMENTS),
    },
    {
        "title": "Requisitions",
        "dataset": "requisitions",
        "blurb": (
            "One row per purchase requisition line. The line total is unit cost "
            "times quantity, computed on load."
        ),
        "columns": sample_rows.REQUISITION_COLUMNS,
        "required": ("requisition_id", "date", "item", "department", "vendor", "unit_cost", "quantity"),
        "rows": sample_rows.REQUISITION_ROWS,
    },
]


def _check_columns_match_the_importer() -> None:
    """Fail loudly if a sheet no longer describes the dataset it claims to.

    This is the whole reason the template is generated rather than hand-kept:
    a column renamed in the importer must not leave a stale template in front
    of a customer.
    """
    for sheet in SHEETS:
        dataset = importer.DATASETS_BY_NAME[sheet["dataset"]]
        headers = [importer._header(name) for name in sheet["columns"]]
        classified = importer.classify_headers(headers)
        if classified is None or classified.name != dataset.name:
            raise SystemExit(
                f"The '{sheet['title']}' columns no longer read as {dataset.name}. "
                "Update SHEETS in this script to match the importer."
            )
        unknown = [name for name, header in zip(sheet["columns"], headers)
                   if header not in dataset.aliases]
        if unknown:
            raise SystemExit(
                f"The '{sheet['title']}' sheet has columns the importer ignores: "
                + ", ".join(unknown)
            )


def _write_sheet(worksheet, spec: dict) -> None:
    columns = spec["columns"]
    last_column = get_column_letter(len(columns))

    worksheet.sheet_view.showGridLines = False
    worksheet.sheet_properties.tabColor = INDIGO

    worksheet.merge_cells(f"A1:{last_column}1")
    title = worksheet["A1"]
    title.value = f"DineAstra {spec['title'].lower()} upload"
    title.font = TITLE_FONT
    title.alignment = Alignment(vertical="center")
    worksheet.row_dimensions[1].height = 26

    worksheet.merge_cells(f"A2:{last_column}2")
    blurb = worksheet["A2"]
    blurb.value = spec["blurb"]
    blurb.font = NOTE_FONT
    blurb.alignment = Alignment(vertical="center", wrap_text=True)
    worksheet.row_dimensions[2].height = 30

    worksheet.merge_cells(f"A3:{last_column}3")
    note = worksheet["A3"]
    note.value = spec.get(
        "note", "Gold headings are required. Keep every column name unchanged."
    )
    note.font = NOTE_FONT

    header_row = 5
    for index, name in enumerate(columns, start=1):
        cell = worksheet.cell(row=header_row, column=index, value=name)
        cell.font = HEADER_FONT
        cell.border = CELL_BORDER
        cell.alignment = Alignment(horizontal="left", vertical="center")
        cell.fill = REQUIRED_FILL if name in spec["required"] else HEADER_FILL
        if name in spec["required"]:
            cell.font = Font(name="Calibri", size=11, bold=True, color=INDIGO_DEEP)
    worksheet.row_dimensions[header_row].height = 22

    for offset, row in enumerate(spec["rows"], start=1):
        for index, value in enumerate(row, start=1):
            cell = worksheet.cell(row=header_row + offset, column=index, value=value)
            cell.border = CELL_BORDER
            if isinstance(value, date):
                cell.number_format = "yyyy-mm-dd"
            if offset % 2 == 0:
                cell.fill = PatternFill("solid", fgColor=PEARL)

    for index, name in enumerate(columns, start=1):
        longest = max(
            [len(name)] + [len(str(row[index - 1])) for row in spec["rows"]]
        )
        worksheet.column_dimensions[get_column_letter(index)].width = min(
            max(longest + 4, 12), 34
        )
    worksheet.freeze_panes = worksheet.cell(row=header_row + 1, column=1)


def build_workbook(path: Path) -> None:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for spec in SHEETS:
        _write_sheet(workbook.create_sheet(spec["title"]), spec)
    workbook.save(path)


def build_delimited_samples(directory: Path) -> None:
    """The CSV and tab-separated equivalents of the daily sheet."""
    daily = SHEETS[0]
    rows = [
        [value.isoformat() if isinstance(value, date) else value for value in row]
        for row in daily["rows"]
    ]

    with (directory / "dineastra_daily_operations_sample.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(daily["columns"])
        writer.writerows(rows)

    with (directory / "dineastra_daily_operations_sample.txt").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(daily["columns"])
        writer.writerows(rows)


def main() -> None:
    _check_columns_match_the_importer()
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    workbook_path = SAMPLES_DIR / "dineastra_daily_operations_template.xlsx"
    build_workbook(workbook_path)
    build_delimited_samples(SAMPLES_DIR)
    print(f"wrote {workbook_path.relative_to(REPO_ROOT)}")
    print(f"      {len(SHEETS)} sheets: " + ", ".join(s["title"] for s in SHEETS))
    print("      plus the CSV and TXT daily samples")


if __name__ == "__main__":
    main()
