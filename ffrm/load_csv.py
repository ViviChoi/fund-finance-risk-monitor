"""
Load a fund and a facility from the CSV files in sample_data/.

Uses only the standard library (csv, os) so it runs on Mac and Windows with
no extra installs. `encoding="utf-8-sig"` quietly handles the byte-order mark
that Excel sometimes adds when you "Save As CSV". All errors raise informative
messages that point the user at the specific CSV file and field at fault.
"""

import csv
import os

from ffrm.models import LP, Asset, Fund, Facility


class CSVDataError(ValueError):
    """Raised when an input CSV is unreadable, empty, or missing required columns."""


def _num(x, default=0.0, field=None, row_idx=None, source=None):
    """Parse a number; raise CSVDataError on garbage rather than silently zeroing."""
    raw = (x or "").strip()
    if raw in ("", "NA", "N/A"):
        return float(default)
    try:
        return float(raw)
    except ValueError:
        loc = f" in {source} row {row_idx} field '{field}'" if source else ""
        raise CSVDataError(
            f"Cannot parse {raw!r} as a number{loc}. "
            f"Tip: open the CSV in Excel, check the cell, save again as CSV."
        ) from None


def _open_csv(path):
    if not os.path.exists(path):
        raise CSVDataError(
            f"Missing input file: {path}. "
            f"Did you keep the sample_data/ folder next to run.py?"
        )
    return open(path, newline="", encoding="utf-8-sig")


def load_fund(data_dir, name="Sample Fund") -> Fund:
    lps_path = os.path.join(data_dir, "investors.csv")
    lps = []
    with _open_csv(lps_path) as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            if not (row.get("name") or "").strip():
                continue
            lps.append(LP(
                name=row["name"].strip(),
                commitment=_num(row.get("commitment"),
                                field="commitment", row_idx=i, source="investors.csv"),
                uncalled=_num(row.get("uncalled"),
                              field="uncalled", row_idx=i, source="investors.csv"),
                rating=(row.get("rating") or "NR").strip(),
            ))
    if not lps:
        raise CSVDataError(
            f"{lps_path} has no LP rows. Expected at least one row with "
            f"columns: name, commitment, uncalled, rating."
        )

    assets_path = os.path.join(data_dir, "assets.csv")
    assets = []
    with _open_csv(assets_path) as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            if not (row.get("name") or "").strip():
                continue
            assets.append(Asset(
                name=row["name"].strip(),
                sector=(row.get("sector") or "Other").strip(),
                nav=_num(row.get("nav"),
                         field="nav", row_idx=i, source="assets.csv"),
                liquidity_days=_num(row.get("liquidity_days"), 30,
                                    field="liquidity_days", row_idx=i, source="assets.csv"),
            ))
    if not assets:
        raise CSVDataError(
            f"{assets_path} has no asset rows. Expected at least one row with "
            f"columns: name, sector, nav, liquidity_days."
        )

    return Fund(name=name, lps=lps, assets=assets)


def load_facility(data_dir) -> Facility:
    path = os.path.join(data_dir, "facility.csv")
    with _open_csv(path) as f:
        reader = csv.DictReader(f)
        try:
            row = next(reader)
        except StopIteration:
            raise CSVDataError(
                f"{path} has no data rows. Expected one row with columns: "
                f"kind, advance_rate, limit, drawn, cure_days."
            ) from None
    return Facility(
        kind=(row.get("kind") or "nav").strip(),
        advance_rate=_num(row.get("advance_rate"), 0.20,
                          field="advance_rate", row_idx=2, source="facility.csv"),
        limit=_num(row.get("limit"), 50,
                   field="limit", row_idx=2, source="facility.csv"),
        drawn=_num(row.get("drawn"), 0,
                   field="drawn", row_idx=2, source="facility.csv"),
        cure_days=int(_num(row.get("cure_days"), 10,
                           field="cure_days", row_idx=2, source="facility.csv")),
    )
