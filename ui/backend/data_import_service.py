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
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORY_PATH = REPO_ROOT / "data" / "runtime" / "import_history.json"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ACCEPTED_SUFFIXES = (".xlsx", ".csv", ".txt")
_LOCK = threading.Lock()


class DataImportError(ValueError):
    pass


ALIASES = {
    "date": "date",
    "business_date": "date",
    "outlet": "outlet",
    "outlet_name": "outlet",
    "net_sales": "net_sales",
    "total_revenue": "net_sales",
    "sales": "net_sales",
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

REQUIRED = (
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
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise DataImportError("The local import history could not be read.") from exc


def _write_history(rows: list[dict]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = HISTORY_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(HISTORY_PATH)


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
    mapped: dict[str, Any] = {}
    for key, value in raw.items():
        canonical = ALIASES.get(_header(key))
        if canonical:
            mapped[canonical] = value

    missing = [key for key in REQUIRED if mapped.get(key) in (None, "")]
    prefix = f"Row {row_number}: " if row_number else ""
    if missing:
        raise DataImportError(prefix + "missing " + ", ".join(missing) + ".")

    try:
        record = {
            "date": _date(mapped["date"]),
            "outlet": str(mapped["outlet"]).strip(),
            "net_sales": round(_number(mapped["net_sales"], "net_sales"), 2),
            "covers": int(_number(mapped["covers"], "covers")),
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
    if record["net_sales"] < 0 or record["covers"] < 0:
        raise DataImportError(prefix + "net_sales and covers cannot be negative.")
    for label in ("food_cost_pct", "labour_cost_pct"):
        if not 0 <= record[label] <= 100:
            raise DataImportError(prefix + f"{label} must be between 0 and 100.")
    if record["checklist_total"] < 0 or not 0 <= record["checklist_signed_off"] <= record["checklist_total"]:
        raise DataImportError(prefix + "checklist_signed_off must be between 0 and checklist_total.")
    return record


def _rows_from_delimited(text: str) -> list[dict]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise DataImportError("The file is empty.")
    try:
        dialect = csv.Sniffer().sniff("\n".join(lines[:5]), delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel_tab if "\t" in lines[0] else csv.excel
    reader = csv.DictReader(io.StringIO("\n".join(lines)), dialect=dialect)
    if not reader.fieldnames:
        raise DataImportError("No header row was found.")
    return [dict(row) for row in reader]


def _rows_from_xlsx(content: bytes) -> list[dict]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise DataImportError("Excel support is not installed on this server.") from exc

    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise DataImportError("The Excel workbook could not be opened.") from exc

    for sheet in workbook.worksheets:
        values = list(sheet.iter_rows(values_only=True))
        for index, row in enumerate(values[:20]):
            headers = [_header(value) for value in row]
            aliases = {ALIASES.get(value) for value in headers}
            if "date" in aliases and "net_sales" in aliases:
                records = []
                for data_row in values[index + 1 :]:
                    if not any(value not in (None, "") for value in data_row):
                        continue
                    records.append(dict(zip(headers, data_row)))
                return records
    raise DataImportError("No data table was found. Keep the sample workbook column names unchanged.")


def parse_upload(filename: str | None, content: bytes) -> list[dict]:
    name = (filename or "").lower()
    if not name.endswith(ACCEPTED_SUFFIXES):
        raise DataImportError("Use an Excel (.xlsx), CSV (.csv), or text (.txt) file.")
    if not content:
        raise DataImportError("The selected file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise DataImportError("The file is larger than the 5 MB demo limit.")

    if name.endswith(".xlsx"):
        raw_rows = _rows_from_xlsx(content)
    else:
        try:
            raw_rows = _rows_from_delimited(content.decode("utf-8-sig"))
        except UnicodeDecodeError as exc:
            raise DataImportError("Save the file as UTF-8 text and upload it again.") from exc

    if not raw_rows:
        raise DataImportError("No data rows were found beneath the header.")
    return [normalize_record(row, index + 2) for index, row in enumerate(raw_rows)]


def ingest(records: list[dict], source_file: str, uploaded_by: str) -> dict:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    batch_id = f"batch-{uuid.uuid4().hex[:8]}"
    created = updated = unchanged = 0

    with _LOCK:
        history = _read_history()
        current = {
            row["business_key"]: row
            for row in history
            if row.get("is_current")
        }

        for payload in records:
            key = f"{payload['date']}|{payload['outlet'].casefold()}"
            existing = current.get(key)
            if existing and existing.get("payload") == payload:
                unchanged += 1
                continue
            if existing:
                existing["is_current"] = False
                existing["valid_to"] = now
                version = int(existing.get("version", 1)) + 1
                updated += 1
            else:
                version = 1
                created += 1

            version_row = {
                "version_id": f"ver-{uuid.uuid4().hex[:10]}",
                "batch_id": batch_id,
                "business_key": key,
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

        if created or updated:
            _write_history(history)

    return {
        "batch_id": batch_id,
        "source_file": source_file,
        "processed": len(records),
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "loaded_at": now,
        "status": "loaded",
    }


def ingest_quick_entry(raw: dict, uploaded_by: str) -> dict:
    record = normalize_record(raw)
    return ingest([record], "Quick entry form", uploaded_by)


def current_records() -> list[dict]:
    return [row["payload"] for row in _read_history() if row.get("is_current")]


def current_daily_rows() -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in current_records():
        grouped[row["date"]].append(row)

    daily = []
    for business_date, rows in sorted(grouped.items()):
        total_revenue = round(sum(row["net_sales"] for row in rows))
        fnb_revenue = total_revenue
        covers = sum(row["covers"] for row in rows)
        food_cost_amount = round(
            sum(row["net_sales"] * row["food_cost_pct"] / 100 for row in rows)
        )
        labor_cost_amount = round(
            sum(row["net_sales"] * row["labour_cost_pct"] / 100 for row in rows)
        )
        checklist_total = sum(row["checklist_total"] for row in rows)
        checklist_signed = sum(row["checklist_signed_off"] for row in rows)
        gop_amount = total_revenue - food_cost_amount - labor_cost_amount
        daily.append(
            {
                "date": business_date,
                "day_of_week": datetime.strptime(business_date, "%Y-%m-%d").strftime("%A"),
                "rooms_available": 0,
                "rooms_sold": 0,
                "occupancy_pct": 0,
                "adr": round(total_revenue / covers, 2) if covers else 0,
                "revpar": 0,
                "room_revenue": 0,
                "fnb_revenue": fnb_revenue,
                "other_revenue": 0,
                "total_revenue": total_revenue,
                "covers": covers,
                "food_cost_pct": round(food_cost_amount / fnb_revenue * 100, 1) if fnb_revenue else 0,
                "food_cost_amount": food_cost_amount,
                "labor_cost_pct": round(labor_cost_amount / total_revenue * 100, 1) if total_revenue else 0,
                "labor_cost_amount": labor_cost_amount,
                "other_cost_amount": 0,
                "gop_amount": gop_amount,
                "gop_pct": round(gop_amount / total_revenue * 100, 1) if total_revenue else 0,
                "checklist_tasks_total": checklist_total,
                "checklist_tasks_signed_off": checklist_signed,
                "checklist_signoff_pct": round(checklist_signed / checklist_total * 100, 1) if checklist_total else 0,
                "outlet_count": len(rows),
            }
        )
    return daily


def status_payload() -> dict:
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
    return {
        "accepted_formats": [".xlsx", ".csv", ".txt"],
        "current_records": len(current),
        "historical_versions": max(0, len(history) - len(current)),
        "outlets": len({row["payload"]["outlet"] for row in current}),
        "latest_date": max((row["payload"]["date"] for row in current), default=None),
        "recent_batches": list(batches.values())[:6],
        "has_uploads": bool(current),
    }
