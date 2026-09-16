"""The one-click sample load behind the "Load sample data" button.

It exists so a visitor can see the intake work before they have a file of
their own. It is deliberately the *same* path an upload takes -- the rows go
through `parse_upload` and `ingest` exactly as a workbook would, so what the
button demonstrates is the real importer and not a shortcut around it.

The rows themselves come from `sample_rows`, which the downloadable workbook
is also built from, so clicking the button and then uploading the downloaded
file reports every row as unchanged rather than as an edit.
"""

from __future__ import annotations

from ui.backend import data_import_service as importer
from ui.backend import sample_rows

SOURCE_NAME = "Sample data (loaded from the dashboard)"


def load(uploaded_by: str) -> dict:
    """Load the sample rows for the workspace being served.

    Returns the same shape an upload does, so the screen can report it the
    same way and the reader sees the identical created / versioned /
    unchanged accounting.
    """
    tables: dict[str, list[dict]] = {}
    for _name, columns, rows in sample_rows.SHEETS:
        csv_text = sample_rows.as_csv(columns, rows)
        parsed = importer.parse_upload("sample.csv", csv_text.encode("utf-8"))
        if parsed.rejects:
            # The sample is covered by a test; a reject here means the sample
            # and the importer have drifted apart, which is a bug in the repo
            # rather than bad input from anybody.
            raise importer.DataImportError(
                "The built-in sample no longer matches the importer: "
                + parsed.rejects[0]["reason"]
            )
        for dataset, accepted in parsed.tables.items():
            tables.setdefault(dataset, []).extend(accepted)

    return importer.ingest(tables, SOURCE_NAME, uploaded_by)
