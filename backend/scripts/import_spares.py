"""Upsert spare-part stock from the plant workbook.

Re-running updates the same rows (sheet area + item name + item group). It
does not insert a second copy. On-hand quantity is set from the sheet. A
minimum quantity entered in the app is left alone. A machine is linked only
when the sheet area is one machine (Flute Laminator, Manual Stitching).

    python -m scripts.import_spares
    python -m scripts.import_spares /path/to/sheet.xlsx

The default file is backend/data/maintenance_spares_24oct2026.xlsx, which
is /app/data/... inside the backend container.
"""

import argparse
import sys
from pathlib import Path

from app.database import SessionLocal
from app.services.spares_import import apply_import, parse_workbook

DEFAULT_XLSX = Path(__file__).resolve().parents[1] / "data" / "maintenance_spares_24oct2026.xlsx"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upsert spare-part stock from the plant xlsx.")
    parser.add_argument("xlsx", nargs="?", default=str(DEFAULT_XLSX), help="Path to the stock workbook")
    args = parser.parse_args(argv)
    path = Path(args.xlsx)
    if not path.is_file():
        print(f"Workbook not found: {path}", file=sys.stderr)
        return 1

    parsed = parse_workbook(path)
    if not parsed.items:
        print(f"No spare rows found in {path}", file=sys.stderr)
        return 1

    for sheet in parsed.sheets:
        extra = ""
        if sheet.duplicate_rows_merged:
            extra += f", {sheet.duplicate_rows_merged} duplicate name(s) combined"
        if sheet.blank_rows_skipped:
            extra += f", {sheet.blank_rows_skipped} blank row(s) skipped"
        if sheet.bad_qty_skipped:
            extra += f", {sheet.bad_qty_skipped} row(s) skipped (qty not a number)"
        print(f"{sheet.category}: {sheet.sheet_rows} sheet rows -> {sheet.items} items{extra}")

    db = SessionLocal()
    try:
        stats = apply_import(db, parsed.items)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    blank = parsed.blank_rows_skipped
    blank_label = "blank row" if blank == 1 else "blank rows"
    print(
        f"Total: {len(parsed.items)} items "
        f"({parsed.sheet_rows} sheet rows, "
        f"{parsed.duplicate_rows_merged} duplicate names combined, "
        f"{blank} {blank_label} skipped)"
    )
    print(f"Created: {stats.created}  Updated: {stats.updated}  Unchanged: {stats.unchanged}")
    for category, machine_name in stats.linked.items():
        count = sum(1 for item in parsed.items if item.category == category)
        print(f"Linked {category} -> {machine_name} ({count})")
    for category, machine_name in stats.missing_machines.items():
        print(f"{category}: no machine named {machine_name!r}; left unlinked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
