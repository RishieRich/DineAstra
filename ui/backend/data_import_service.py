"""Operational data intake with a compact type-2 history model.

Each business key is the combination of date and outlet. Uploading a changed
row closes the previous version and opens a new current version. Unchanged
rows are skipped. The current records are aggregated by date for the metric
registry, so the dashboard and Ask AI read the same imported facts.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import threading
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from ui.backend import store

REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ACCEPTED_SUFFIXES = (".xlsx", ".csv", ".txt")
_LOCK = threading.Lock()


class DataImportError(ValueError):
    pass


DAILY_ALIASES = {
    "date": "date",
    "business_date": "date",
    "outlet": "outlet",
    "outlet_name": "outlet",
    "net_sales": "net_sales",
    "dine_in_sales": "net_sales",
    "total_revenue": "net_sales",
    "sales": "net_sales",
    "delivery_sales": "delivery_sales",
    "delivery_revenue": "delivery_sales",
    "covers": "covers",
    "food_cost_pct": "food_cost_pct",
    "food_cost_percent": "food_cost_pct",
    "labour_cost_pct": "labour_cost_pct",
    "labor_cost_pct": "labour_cost_pct",
    "checklist_total": "checklist_total",
    "checklist_tasks_total": "checklist_total",
    "checklist_signed_off": "checklist_signed_off",
    "checklist_tasks_signed_off": "checklist_signed_off",
    "notes": "notes",
}

DAILY_REQUIRED = (
    "date",
    "outlet",
    "net_sales",
    "covers",
    "food_cost_pct",
    "labour_cost_pct",
    "checklist_total",
    "checklist_signed_off",
)


def _header(value: Any) -> str:
    text = str(value or "").strip().lower().replace("%", " pct ")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _read_history() -> list[dict]:
    """Every version row for the workspace being served, oldest first."""
    try:
        return store.get_store().read_all(store.current_workspace())
    except DataImportError:
        raise
    except Exception as exc:  # a missing table, a dropped connection, bad JSON
        raise DataImportError(
            "The import history could not be read. If this is a fresh "
            "deployment, check that DATABASE_URL is set and reachable."
        ) from exc


def _write_history(rows: list[dict]) -> None:
    try:
        store.get_store().replace_all(store.current_workspace(), rows)
    except Exception as exc:
        raise DataImportError("The import history could not be saved.") from exc


def _date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise DataImportError(f"'{text}' is not a recognised date. Use YYYY-MM-DD.")


def _number(value: Any, label: str) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value or "").strip().replace(",", "").replace("₹", "")
    try:
        return float(text)
    except ValueError as exc:
        raise DataImportError(f"{label} must be numeric.") from exc


def normalize_record(raw: dict, row_number: int | None = None) -> dict:
    mapped = _map_columns(raw, DAILY_ALIASES)
    missing = [key for key in DAILY_REQUIRED if mapped.get(key) in (None, "")]
    prefix = f"Row {row_number}: " if row_number else ""
    if missing:
        raise DataImportError(prefix + "missing " + ", ".join(missing) + ".")

    try:
        record = {
            "date": _date(mapped["date"]),
            "outlet": str(mapped["outlet"]).strip(),
            "net_sales": round(_number(mapped["net_sales"], "net_sales"), 2),
            "covers": int(_number(mapped["covers"], "covers")),
            "delivery_sales": round(
                _number(mapped.get("delivery_sales") or 0, "delivery_sales"), 2
            ),
            "food_cost_pct": round(_number(mapped["food_cost_pct"], "food_cost_pct"), 2),
            "labour_cost_pct": round(_number(mapped["labour_cost_pct"], "labour_cost_pct"), 2),
            "checklist_total": int(_number(mapped["checklist_total"], "checklist_total")),
            "checklist_signed_off": int(
                _number(mapped["checklist_signed_off"], "checklist_signed_off")
            ),
            "notes": str(mapped.get("notes") or "").strip(),
        }
    except DataImportError as exc:
        raise DataImportError(prefix + str(exc)) from exc

    if not record["outlet"]:
        raise DataImportError(prefix + "outlet cannot be blank.")
    if record["net_sales"] < 0 or record["covers"] < 0 or record["delivery_sales"] < 0:
        raise DataImportError(prefix + "sales and covers cannot be negative.")
    for label in ("food_cost_pct", "labour_cost_pct"):
        if not 0 <= record[label] <= 100:
            raise DataImportError(prefix + f"{label} must be between 0 and 100.")
    if record["checklist_total"] < 0 or not 0 <= record["checklist_signed_off"] <= record["checklist_total"]:
        raise DataImportError(prefix + "checklist_signed_off must be between 0 and checklist_total.")
    return record


EVENT_ALIASES = {
    "event_id": "event_id",
    "id": "event_id",
    "booking_id": "event_id",
    "event_name": "name",
    "name": "name",
    "segment": "segment",
    "market_segment": "segment",
    "date": "date",
    "event_date": "date",
    "covers": "covers",
    "guests": "covers",
    "venue": "venue",
    "revenue": "revenue",
    "event_revenue": "revenue",
    "contracted_revenue": "revenue",
    "food_cost": "food_cost",
    "beverage_cost": "beverage_cost",
    "labour_cost": "labor_cost",
    "labor_cost": "labor_cost",
    "other_cost": "other_cost",
}

EVENT_REQUIRED = ("event_id", "name", "segment", "date", "covers", "revenue", "food_cost")

# banquet-policy.md 3.1 recognises these four, and sets a margin floor for each.
# An unknown segment is refused rather than quietly bucketed, because there
# would be no floor to judge it against.
EVENT_SEGMENTS = ("corporate", "group", "wedding", "celebration")

REQUISITION_ALIASES = {
    "requisition_id": "requisition_id",
    "id": "requisition_id",
    "submission_id": "requisition_id",
    "date": "date",
    "requisition_date": "date",
    "item": "item",
    "item_name": "item",
    "department": "department",
    "vendor": "vendor",
    "supplier": "vendor",
    "unit_cost": "unit_cost",
    "rate": "unit_cost",
    "quantity": "quantity",
    "qty": "quantity",
}

REQUISITION_REQUIRED = (
    "requisition_id",
    "date",
    "item",
    "department",
    "vendor",
    "unit_cost",
    "quantity",
)


def _map_columns(raw: dict, aliases: dict) -> dict:
    mapped: dict[str, Any] = {}
    for key, value in raw.items():
        canonical = aliases.get(_header(key))
        if canonical:
            mapped[canonical] = value
    return mapped


def normalize_event(raw: dict, row_number: int | None = None) -> dict:
    """One banquet event row.

    Net and margin are computed from the costs rather than read from the sheet.
    A spreadsheet's own margin column is someone else's arithmetic, and the
    product's claim is that a figure is computed here or not shown at all.
    """
    mapped = _map_columns(raw, EVENT_ALIASES)
    prefix = f"Row {row_number}: " if row_number else ""
    missing = [key for key in EVENT_REQUIRED if mapped.get(key) in (None, "")]
    if missing:
        raise DataImportError(prefix + "missing " + ", ".join(missing) + ".")

    try:
        segment = str(mapped["segment"]).strip().casefold()
        record = {
            "id": str(mapped["event_id"]).strip(),
            "name": str(mapped["name"]).strip(),
            "segment": segment,
            "date": _date(mapped["date"]),
            "covers": int(_number(mapped["covers"], "covers")),
            "delivery_sales": round(
                _number(mapped.get("delivery_sales") or 0, "delivery_sales"), 2
            ),
            "venue": str(mapped.get("venue") or "").strip(),
            "revenue": round(_number(mapped["revenue"], "revenue")),
            "food_cost": round(_number(mapped["food_cost"], "food_cost")),
            "beverage_cost": round(_number(mapped.get("beverage_cost") or 0, "beverage_cost")),
            "labor_cost": round(_number(mapped.get("labor_cost") or 0, "labor_cost")),
            "other_cost": round(_number(mapped.get("other_cost") or 0, "other_cost")),
        }
    except DataImportError as exc:
        raise DataImportError(prefix + str(exc)) from exc

    if not record["id"]:
        raise DataImportError(prefix + "event_id cannot be blank.")
    if segment not in EVENT_SEGMENTS:
        raise DataImportError(prefix + "segment must be one of " + ", ".join(EVENT_SEGMENTS) + ".")
    if record["revenue"] <= 0:
        raise DataImportError(prefix + "revenue must be greater than zero.")
    if record["covers"] < 0:
        raise DataImportError(prefix + "covers cannot be negative.")
    cost_keys = ("food_cost", "beverage_cost", "labor_cost", "other_cost")
    if any(record[key] < 0 for key in cost_keys):
        raise DataImportError(prefix + "event costs cannot be negative.")

    record["net"] = record["revenue"] - sum(record[key] for key in cost_keys)
    record["margin_pct"] = round(record["net"] / record["revenue"] * 100, 1)
    return record


def normalize_requisition(raw: dict, row_number: int | None = None) -> dict:
    """One requisition line. The total is unit cost times quantity, computed here."""
    mapped = _map_columns(raw, REQUISITION_ALIASES)
    prefix = f"Row {row_number}: " if row_number else ""
    missing = [key for key in REQUISITION_REQUIRED if mapped.get(key) in (None, "")]
    if missing:
        raise DataImportError(prefix + "missing " + ", ".join(missing) + ".")

    try:
        record = {
            "id": str(mapped["requisition_id"]).strip(),
            "date": _date(mapped["date"]),
            "item": str(mapped["item"]).strip(),
            "department": str(mapped["department"]).strip(),
            "vendor": str(mapped["vendor"]).strip(),
            "unit_cost": round(_number(mapped["unit_cost"], "unit_cost"), 2),
            "quantity": int(_number(mapped["quantity"], "quantity")),
        }
    except DataImportError as exc:
        raise DataImportError(prefix + str(exc)) from exc

    if not record["id"]:
        raise DataImportError(prefix + "requisition_id cannot be blank.")
    if record["unit_cost"] < 0 or record["quantity"] < 0:
        raise DataImportError(prefix + "unit_cost and quantity cannot be negative.")
    record["total_cost"] = round(record["unit_cost"] * record["quantity"], 2)
    return record


@dataclass(frozen=True)
class Dataset:
    """One kind of record a sheet or file can carry."""

    name: str
    label: str
    aliases: dict
    # The canonical columns that mark a table as this dataset. A sheet is read
    # as events only if it carries all of them, so an unrelated sheet in the
    # customer's own workbook is skipped rather than misread.
    signature: tuple
    normalize: Any
    key: Any


DATASETS = (
    Dataset(
        name="daily",
        label="Daily operations",
        aliases=DAILY_ALIASES,
        signature=("date", "outlet", "net_sales"),
        normalize=normalize_record,
        key=lambda record: record["date"] + "|" + record["outlet"].casefold(),
    ),
    Dataset(
        name="events",
        label="Events",
        aliases=EVENT_ALIASES,
        signature=("event_id", "segment", "revenue"),
        normalize=normalize_event,
        key=lambda record: record["id"].casefold(),
    ),
    Dataset(
        name="requisitions",
        label="Requisitions",
        aliases=REQUISITION_ALIASES,
        signature=("requisition_id", "item", "unit_cost"),
        normalize=normalize_requisition,
        key=lambda record: record["id"].casefold(),
    ),
)

DATASETS_BY_NAME = {dataset.name: dataset for dataset in DATASETS}
DEFAULT_DATASET = "daily"


def classify_headers(headers: list[str]) -> Dataset | None:
    """Which dataset, if any, a row of column names describes.

    Datasets are tried in order and the first whose whole signature is present
    wins. `id` and `date` are shared between them, so each signature is built
    from the columns that are not shared.
    """
    for dataset in DATASETS:
        canonical = {dataset.aliases.get(header) for header in headers}
        if all(field in canonical for field in dataset.signature):
            return dataset
    return None


def _table_from_rows(values: list[tuple]) -> tuple[Dataset, list[dict]] | None:
    """Find the header row in a block of cells and read the table under it.

    Customer workbooks put a title, a note and a blank row above the data, so
    the header is looked for in the first twenty rows rather than assumed to
    be the first one.
    """
    for index, row in enumerate(values[:20]):
        headers = [_header(value) for value in row]
        dataset = classify_headers(headers)
        if dataset is None:
            continue
        records = []
        for data_row in values[index + 1 :]:
            if not any(value not in (None, "") for value in data_row):
                continue
            records.append(dict(zip(headers, data_row)))
        return dataset, records
    return None


def _tables_from_delimited(text: str) -> list[tuple[Dataset, list[dict]]]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise DataImportError("The file is empty.")
    try:
        dialect = csv.Sniffer().sniff("\n".join(lines[:5]), delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel_tab if "\t" in lines[0] else csv.excel
    reader = csv.reader(io.StringIO("\n".join(lines)), dialect=dialect)
    values = [tuple(row) for row in reader]
    if not values:
        raise DataImportError("No header row was found.")

    table = _table_from_rows(values)
    if table is None:
        raise DataImportError(
            "No data table was found. Keep the sample column names unchanged."
        )
    return [table]


def _tables_from_xlsx(content: bytes) -> list[tuple[Dataset, list[dict]]]:
    """Every recognised table in the workbook, one per sheet.

    A workbook may carry daily operations, events and requisitions on separate
    sheets, and a customer's own extra sheets alongside them. Each sheet is
    classified on its own and anything unrecognised is skipped in silence --
    it is not the importer's business what else is in their workbook.
    """
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise DataImportError("Excel support is not installed on this server.") from exc

    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise DataImportError("The Excel workbook could not be opened.") from exc

    tables: list[tuple[Dataset, list[dict]]] = []
    seen: set[str] = set()
    for sheet in workbook.worksheets:
        table = _table_from_rows(list(sheet.iter_rows(values_only=True)))
        if table is None:
            continue
        dataset, rows = table
        if dataset.name in seen:
            # Two sheets of the same kind would need a merge order nobody has
            # specified, so say so rather than pick one.
            raise DataImportError(
                f"This workbook has more than one {dataset.label} sheet. "
                "Keep one sheet per kind of record."
            )
        seen.add(dataset.name)
        tables.append(table)

    if not tables:
        raise DataImportError(
            "No data table was found. Keep the sample workbook column names unchanged."
        )
    return tables


@dataclass
class ParseResult:
    """What a file yielded: the rows that passed, and the rows that did not.

    A bad row is not a bad file. One mistyped percentage in a month of trade
    should not send the whole workbook back, so rows are judged individually
    and the reader gets both halves of the answer.
    """

    tables: dict[str, list[dict]]
    rejects: list[dict]

    @property
    def records(self) -> list[dict]:
        """The accepted daily-operations rows, the common case."""
        return self.tables.get(DEFAULT_DATASET, [])

    @property
    def accepted(self) -> int:
        return sum(len(rows) for rows in self.tables.values())

    @property
    def has_rejects(self) -> bool:
        return bool(self.rejects)


def parse_upload(filename: str | None, content: bytes) -> ParseResult:
    """Read a file into accepted records and rejected rows.

    Anything wrong with the *file* still raises -- an unreadable workbook has
    no rows to salvage. Anything wrong with a *row* is collected instead, so a
    partial load can go ahead and the reader can be told exactly what was left
    out and why.
    """
    name = (filename or "").lower()
    if not name.endswith(ACCEPTED_SUFFIXES):
        raise DataImportError("Use an Excel (.xlsx), CSV (.csv), or text (.txt) file.")
    if not content:
        raise DataImportError("The selected file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise DataImportError("The file is larger than the 5 MB demo limit.")

    if name.endswith(".xlsx"):
        tables = _tables_from_xlsx(content)
    else:
        try:
            tables = _tables_from_delimited(content.decode("utf-8-sig"))
        except UnicodeDecodeError as exc:
            raise DataImportError("Save the file as UTF-8 text and upload it again.") from exc

    if not any(rows for _, rows in tables):
        raise DataImportError("No data rows were found beneath the header.")

    accepted: dict[str, list[dict]] = {}
    rejects: list[dict] = []
    for dataset, raw_rows in tables:
        rows: list[dict] = []
        for index, raw in enumerate(raw_rows):
            # Row 1 is the header, so the first data row is row 2 in the
            # reader's spreadsheet. Report the number they can go and look at.
            row_number = index + 2
            try:
                rows.append(dataset.normalize(raw, row_number))
            except DataImportError as exc:
                rejects.append(
                    {
                        "dataset": dataset.name,
                        "sheet": dataset.label,
                        "row": row_number,
                        "reason": str(exc).replace(f"Row {row_number}: ", ""),
                        "values": {
                            str(key): ("" if value is None else str(value))
                            for key, value in raw.items()
                            if key
                        },
                    }
                )
        accepted[dataset.name] = rows

    # A file where every row failed is not an error to throw away -- it is the
    # case where the reader most needs the report. It comes back like any other
    # partial load, with nothing accepted and every reason listed.
    return ParseResult(tables=accepted, rejects=rejects)


REJECT_REPORT_COLUMNS = ("sheet", "row", "reason")


def reject_report_csv(rejects: list[dict]) -> str:
    """The rejected rows as a CSV the reader can open, fix, and re-upload.

    Every column the original row carried is preserved next to the reason, so
    the report doubles as the correction sheet rather than just a complaint.
    """
    value_columns: list[str] = []
    for reject in rejects:
        for key in reject.get("values", {}):
            if key not in value_columns:
                value_columns.append(key)

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([*REJECT_REPORT_COLUMNS, *value_columns])
    for reject in rejects:
        values = reject.get("values", {})
        writer.writerow(
            [
                reject.get("sheet", ""),
                reject["row"],
                reject["reason"],
                *(values.get(key, "") for key in value_columns),
            ]
        )
    return buffer.getvalue()


def ingest(
    tables: dict[str, list[dict]] | list[dict],
    source_file: str,
    uploaded_by: str,
) -> dict:
    """Load accepted records, versioning any business key that changed.

    Accepts either the per-dataset mapping a ParseResult carries, or a bare
    list of daily rows, which is what the quick-entry form produces.
    """
    if isinstance(tables, list):
        tables = {DEFAULT_DATASET: tables}

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    batch_id = f"batch-{uuid.uuid4().hex[:8]}"
    created = updated = unchanged = 0
    per_dataset: dict[str, dict] = {}

    with _LOCK:
        history = _read_history()
        current = {
            (row.get("dataset", DEFAULT_DATASET), row["business_key"]): row
            for row in history
            if row.get("is_current")
        }

        for dataset_name, records in tables.items():
            dataset = DATASETS_BY_NAME[dataset_name]
            counts = {"created": 0, "updated": 0, "unchanged": 0, "processed": len(records)}
            for payload in records:
                key = (dataset_name, dataset.key(payload))
                existing = current.get(key)
                if existing and existing.get("payload") == payload:
                    counts["unchanged"] += 1
                    continue
                if existing:
                    existing["is_current"] = False
                    existing["valid_to"] = now
                    version = int(existing.get("version", 1)) + 1
                    counts["updated"] += 1
                else:
                    version = 1
                    counts["created"] += 1

                version_row = {
                    "version_id": f"ver-{uuid.uuid4().hex[:10]}",
                    "batch_id": batch_id,
                    "dataset": dataset_name,
                    "business_key": key[1],
                    "version": version,
                    "valid_from": now,
                    "valid_to": None,
                    "is_current": True,
                    "source_file": source_file,
                    "uploaded_by": uploaded_by,
                    "content_hash": hashlib.sha256(
                        json.dumps(payload, sort_keys=True).encode("utf-8")
                    ).hexdigest()[:12],
                    "payload": payload,
                }
                history.append(version_row)
                current[key] = version_row

            created += counts["created"]
            updated += counts["updated"]
            unchanged += counts["unchanged"]
            if counts["processed"]:
                per_dataset[dataset_name] = {"label": dataset.label, **counts}

        if created or updated:
            _write_history(history)

    return {
        "batch_id": batch_id,
        "source_file": source_file,
        "processed": sum(len(records) for records in tables.values()),
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "datasets": per_dataset,
        "loaded_at": now,
        "status": "loaded",
    }


def ingest_quick_entry(raw: dict, uploaded_by: str) -> dict:
    record = normalize_record(raw)
    return ingest([record], "Quick entry form", uploaded_by)


def current_records(dataset: str = DEFAULT_DATASET) -> list[dict]:
    """The latest accepted version of every business key in one dataset."""
    return [
        row["payload"]
        for row in _read_history()
        if row.get("is_current") and row.get("dataset", DEFAULT_DATASET) == dataset
    ]


def current_events() -> list[dict]:
    return current_records("events")


def current_requisitions() -> list[dict]:
    return current_records("requisitions")


def current_daily_rows() -> list[dict]:
    """The accepted outlet rows aggregated to one trading day each.

    An uploaded day is a complete day for the outlets it covers: dining room
    sales, delivery, covers, the two cost percentages and the checklist. The
    one thing it cannot know is the estate's seat count, so the per-seat
    figures are left to `overlay_daily_row` to decide.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in current_records():
        grouped[row["date"]].append(row)

    daily = []
    for business_date, rows in sorted(grouped.items()):
        dine_in_revenue = round(sum(row["net_sales"] for row in rows))
        delivery_revenue = round(sum(row.get("delivery_sales", 0) for row in rows))
        total_revenue = dine_in_revenue + delivery_revenue
        covers = sum(row["covers"] for row in rows)

        # The two cost percentages on the sheet are stated against that
        # outlet's whole day, delivery included -- that is how an operator
        # reads a P&L. Applying them to dine-in alone would understate the
        # rupee cost and hand back a percentage lower than the one they typed.
        def _outlet_total(row: dict) -> float:
            return row["net_sales"] + row.get("delivery_sales", 0)

        food_cost_amount = round(
            sum(_outlet_total(row) * row["food_cost_pct"] / 100 for row in rows)
        )
        labour_cost_amount = round(
            sum(_outlet_total(row) * row["labour_cost_pct"] / 100 for row in rows)
        )
        food_cost_pct = round(food_cost_amount / total_revenue * 100, 1) if total_revenue else 0
        labour_cost_pct = round(labour_cost_amount / total_revenue * 100, 1) if total_revenue else 0
        daily.append(
            {
                "date": business_date,
                "day_of_week": datetime.strptime(business_date, "%Y-%m-%d").strftime("%A"),
                "covers": covers,
                "dine_in_revenue": dine_in_revenue,
                "delivery_revenue": delivery_revenue,
                "events_revenue": 0,
                "total_revenue": total_revenue,
                "average_order_value": round(total_revenue / covers, 2) if covers else 0,
                "delivery_mix_pct": (
                    round(delivery_revenue / total_revenue * 100, 1) if total_revenue else 0
                ),
                "food_cost_pct": food_cost_pct,
                "food_cost_amount": food_cost_amount,
                "labor_cost_pct": labour_cost_pct,
                "labor_cost_amount": labour_cost_amount,
                "prime_cost_pct": round(food_cost_pct + labour_cost_pct, 1),
                "prime_cost_amount": food_cost_amount + labour_cost_amount,
                "checklist_tasks_total": sum(row["checklist_total"] for row in rows),
                "checklist_tasks_signed_off": sum(row["checklist_signed_off"] for row in rows),
                "outlet_count": len(rows),
                "source": "Data Studio",
            }
        )
    return daily


# Overhead is not something an outlet sheet reports, so the operating margin
# of an uploaded day is struck after prime cost only, at the rate the seeded
# estate runs at. Stated here rather than buried in the arithmetic.
ASSUMED_OVERHEAD_PCT = 18.5


def overlay_daily_row(seeded: dict | None, imported: dict) -> dict:
    """Lay one aggregated upload over the seeded row for the same date.

    An upload supersedes the sample day entirely -- it is the customer's own
    trade, and every figure on a restaurant day comes from the same sheet.
    The exceptions are the facts about the estate rather than the day: the
    seat count is carried over from the seeded row, and where there is no
    seeded row the per-seat figures are reported as unknown rather than zero,
    because nobody told us how many seats were trading.
    """
    row = dict(imported)
    seats = (seeded or {}).get("seats")
    row["seats"] = seats
    row["sales_per_seat"] = (
        round(row["dine_in_revenue"] / seats, 2) if seats else None
    )
    row["table_turns"] = round(row["covers"] / seats, 2) if seats else None

    total_revenue = row["total_revenue"]
    overhead_amount = round(total_revenue * ASSUMED_OVERHEAD_PCT / 100)
    row["overhead_amount"] = overhead_amount
    gop_amount = total_revenue - row["prime_cost_amount"] - overhead_amount
    row["gop_amount"] = gop_amount
    row["gop_pct"] = round(gop_amount / total_revenue * 100, 1) if total_revenue else 0

    # Comps and voids are not on the daily sheet; absent, not zero.
    row["void_comp_pct"] = None
    row["void_comp_amount"] = None

    total_tasks = row["checklist_tasks_total"]
    row["checklist_signoff_pct"] = (
        round(row["checklist_tasks_signed_off"] / total_tasks * 100, 1)
        if total_tasks
        else 0
    )
    return row


def status_payload() -> dict:
    """What has been loaded, per dataset and overall."""
    history = _read_history()
    current = [row for row in history if row.get("is_current")]

    batches: dict[str, dict] = {}
    for row in reversed(history):
        batch_id = row.get("batch_id")
        if not batch_id or batch_id in batches:
            continue
        batches[batch_id] = {
            "batch_id": batch_id,
            "source_file": row.get("source_file"),
            "loaded_at": row.get("valid_from"),
            "uploaded_by": row.get("uploaded_by"),
        }

    per_dataset = {}
    for dataset in DATASETS:
        rows = [
            row for row in current
            if row.get("dataset", DEFAULT_DATASET) == dataset.name
        ]
        if not rows:
            continue
        per_dataset[dataset.name] = {
            "label": dataset.label,
            "records": len(rows),
            "latest_date": max(
                (row["payload"]["date"] for row in rows if row["payload"].get("date")),
                default=None,
            ),
        }

    daily = [
        row for row in current
        if row.get("dataset", DEFAULT_DATASET) == DEFAULT_DATASET
    ]
    return {
        "accepted_formats": [".xlsx", ".csv", ".txt"],
        "current_records": len(current),
        "historical_versions": max(0, len(history) - len(current)),
        # Outlets are a daily-operations idea; an event row has a venue instead.
        "outlets": len({row["payload"]["outlet"] for row in daily}),
        "latest_date": max(
            (row["payload"]["date"] for row in current if row["payload"].get("date")),
            default=None,
        ),
        "datasets": per_dataset,
        "recent_batches": list(batches.values())[:6],
        "has_uploads": bool(current),
    }


def store_reject_report(batch_id: str, rejects: list[dict]) -> str | None:
    """Keep a batch's reject report so the reader can download it.

    Reports hold the customer's own rows, so they are scoped to the workspace
    that produced them and go wherever the import history goes.
    """
    if not rejects:
        return None
    store.get_store().put_report(
        store.current_workspace(), batch_id, reject_report_csv(rejects)
    )
    return batch_id


def load_reject_report(batch_id: str) -> str | None:
    """The stored report for a batch, or None if there was nothing to reject."""
    if not re.fullmatch(r"batch-[0-9a-f]{8}", batch_id or ""):
        return None
    return store.get_store().get_report(store.current_workspace(), batch_id)


RESET_CONFIRMATION_PHRASE = "RESET"


def reset_to_sample(confirmation: str) -> dict:
    """Discard every uploaded record and return to the seeded sample data.

    Destructive and not undoable, so it refuses unless the caller repeats the
    confirmation phrase exactly. The import history and every stored reject
    report are removed together -- leaving the reports behind would offer
    downloads for batches that no longer exist.
    """
    if (confirmation or "").strip() != RESET_CONFIRMATION_PHRASE:
        raise DataImportError(
            f"Type {RESET_CONFIRMATION_PHRASE} to confirm. "
            "This removes every uploaded record and cannot be undone."
        )

    with _LOCK:
        history = _read_history()
        removed_versions = len(history)
        removed_current = len([row for row in history if row.get("is_current")])
        reports_removed = len({row.get("batch_id") for row in history if row.get("batch_id")})
        store.get_store().clear(store.current_workspace())

    return {
        "status": "reset",
        "removed_current_records": removed_current,
        "removed_versions": removed_versions,
        "removed_reject_reports": reports_removed,
        "reset_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
