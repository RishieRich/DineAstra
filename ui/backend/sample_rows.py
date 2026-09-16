"""The sample rows, defined once.

Two things hand these to a customer: the "Load sample data" button, which
pushes them straight through the importer, and the downloadable workbook,
which they open in Excel. Those were separate copies and drifted apart in
their note text within a day of being written -- so loading the sample and
then uploading the downloaded template reported rows as *changed* when
nothing had changed.

Keeping one definition here means the button and the file are the same rows
by construction, and the demo's "upload it twice, nothing is duplicated"
moment stays true across both paths.

Rows are dated after the seeded window on purpose. They add trading days
rather than restating a day DEMO.md already quotes.
"""

from __future__ import annotations

import csv
import io
from datetime import date

DAILY_COLUMNS = [
    "date",
    "outlet",
    "dine_in_sales",
    "delivery_sales",
    "covers",
    "food_cost_pct",
    "labour_cost_pct",
    "checklist_total",
    "checklist_signed_off",
    "notes",
]

DAILY_ROWS = [
    [date(2026, 9, 15), "Astra House, Indiranagar", 214600, 48200, 182, 33.9, 26.4, 12, 12, "Chef's table at 8pm"],
    [date(2026, 9, 16), "Astra House, Indiranagar", 198400, 52700, 169, 34.6, 27.1, 12, 11, "Walk-in covers down on a wet evening"],
    [date(2026, 9, 15), "Astra Terrace, Koramangala", 171900, 36400, 131, 34.1, 25.8, 10, 10, "Bar led the evening"],
    [date(2026, 9, 16), "Astra Terrace, Koramangala", 164300, 39800, 124, 34.8, 26.3, 10, 10, "Rain cut the deck covers"],
    [date(2026, 9, 15), "Astra Cafe, Whitefield", 76200, 41300, 147, 32.8, 24.9, 12, 12, "Delivery ahead of dine-in"],
    [date(2026, 9, 16), "Astra Cafe, Whitefield", 71500, 44100, 138, 33.2, 25.4, 12, 11, "Late opening; one task missed"],
]

EVENT_COLUMNS = [
    "event_id",
    "event_name",
    "segment",
    "date",
    "covers",
    "venue",
    "revenue",
    "food_cost",
    "beverage_cost",
    "labour_cost",
    "other_cost",
]

EVENT_ROWS = [
    ["BQ-2026-101", "Meridian Systems Leadership Dinner", "corporate", date(2026, 9, 15), 42, "Astra House, Private Room", 186000, 44500, 15200, 21800, 8400],
    ["BQ-2026-102", "Sharma Anniversary Dinner", "celebration", date(2026, 9, 16), 28, "Astra Terrace, Sky Room", 74000, 22800, 7600, 9400, 3800],
    ["BQ-2026-103", "Whitefield Supper Club", "group", date(2026, 9, 16), 34, "Astra Cafe, Whitefield", 61000, 16200, 5100, 7900, 2600],
]

REQUISITION_COLUMNS = [
    "requisition_id",
    "date",
    "item",
    "department",
    "vendor",
    "unit_cost",
    "quantity",
]

REQUISITION_ROWS = [
    ["SUB-004201", date(2026, 9, 15), "Basmati Rice 1kg", "Kitchen", "Anand Grain Traders", 61, 38],
    ["SUB-004202", date(2026, 9, 15), "Fresh Paneer 1kg", "Kitchen", "Himalayan Dairy Co", 340, 22],
    ["SUB-004203", date(2026, 9, 16), "Delivery Packaging - Meal Box (100)", "Delivery & Packaging", "EcoPack Solutions", 495, 30],
]

SHEETS = (
    ("daily", DAILY_COLUMNS, DAILY_ROWS),
    ("events", EVENT_COLUMNS, EVENT_ROWS),
    ("requisitions", REQUISITION_COLUMNS, REQUISITION_ROWS),
)


def as_csv(columns: list[str], rows: list[list]) -> str:
    """One sheet as CSV text, quoted the way a spreadsheet would export it."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow(
            [value.isoformat() if isinstance(value, date) else value for value in row]
        )
    return buffer.getvalue()
