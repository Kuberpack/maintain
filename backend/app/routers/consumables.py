import csv
import io
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import get_current_user, require_roles
from app.database import get_db
from app.models import User, UserRole
from app.schemas.consumables import (
    CloseLineIn,
    ConfirmSlipIn,
    ConsumableItemCreate,
    ConsumableItemPublic,
    ConsumableItemUpdate,
    ConsumablePolicyPublic,
    DailySheet,
    InwardCreate,
    LeakageReport,
    ReturnCreate,
    ShiftInfo,
    SlipCreate,
    SlipCreated,
    SlipPublic,
    StockCountCreate,
    StockCountPublic,
)
from app.services.consumables import (
    SHIFT_HOURS,
    SHIFT_START,
    SHIFTS,
    ConsumableError,
    close_line,
    confirm_slip,
    count_public,
    create_item,
    create_slip,
    daily_sheet,
    item_public,
    leakage_report,
    list_counts,
    list_items,
    list_slips,
    receive_inward,
    record_count,
    require_slip,
    return_core,
    return_material,
    slip_public,
    update_item,
)

router = APIRouter(prefix="/consumables", tags=["consumables"])

_stock_roles = require_roles(UserRole.supervisor, UserRole.management, UserRole.admin)
_report_roles = require_roles(UserRole.management, UserRole.admin)
_issue_roles = require_roles(UserRole.supervisor, UserRole.management, UserRole.admin)


def _run(fn):
    try:
        return fn()
    except ConsumableError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


def _shifts() -> list[ShiftInfo]:
    labels = {"A": "Shift A", "B": "Shift B", "C": "Shift C"}
    rows: list[ShiftInfo] = []
    for code in SHIFTS:
        start = SHIFT_START[code]
        end_hour = (start.hour + SHIFT_HOURS) % 24
        rows.append(
            ShiftInfo(
                id=code,
                label=labels[code],
                starts=start.strftime("%H:%M"),
                ends=f"{end_hour:02d}:{start.minute:02d}",
            )
        )
    return rows


@router.get("/policy", response_model=ConsumablePolicyPublic)
def get_policy(_user: User = Depends(get_current_user)) -> ConsumablePolicyPublic:
    return ConsumablePolicyPublic(core_policy=get_settings().consumable_core_policy, shifts=_shifts())


@router.get("/items", response_model=list[ConsumableItemPublic])
def get_items(
    search: str | None = None,
    item_group: str | None = Query(default=None, alias="itemGroup"),
    low_stock: bool = Query(default=False, alias="lowStock"),
    include_inactive: bool = Query(default=False, alias="includeInactive"),
    db: Session = Depends(get_db),
    _user: User = Depends(_stock_roles),
) -> list[ConsumableItemPublic]:
    items = list_items(db, search=search, item_group=item_group, low_stock=low_stock, include_inactive=include_inactive)
    return [item_public(item) for item in items]


@router.post("/items", response_model=ConsumableItemPublic, status_code=201)
def post_item(
    payload: ConsumableItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_stock_roles),
) -> ConsumableItemPublic:
    item = _run(lambda: create_item(db, payload, user))
    return item_public(item)


@router.patch("/items/{item_id}", response_model=ConsumableItemPublic)
def patch_item(
    item_id: uuid.UUID,
    payload: ConsumableItemUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(_stock_roles),
) -> ConsumableItemPublic:
    item = _run(lambda: update_item(db, item_id, payload))
    return item_public(item)


@router.post("/items/{item_id}/inward", response_model=ConsumableItemPublic)
def post_inward(
    item_id: uuid.UUID,
    payload: InwardCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_stock_roles),
) -> ConsumableItemPublic:
    item = _run(lambda: receive_inward(db, item_id, payload, user))
    return item_public(item)


@router.post("/items/{item_id}/counts", response_model=StockCountPublic, status_code=201)
def post_count(
    item_id: uuid.UUID,
    payload: StockCountCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_stock_roles),
) -> StockCountPublic:
    row = _run(lambda: record_count(db, item_id, payload, user))
    return count_public(row)


@router.get("/items/{item_id}/counts", response_model=list[StockCountPublic])
def get_counts(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(_stock_roles),
) -> list[StockCountPublic]:
    rows = _run(lambda: list_counts(db, item_id))
    return [count_public(row) for row in rows]


@router.get("/slips", response_model=list[SlipPublic])
def get_slips(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[SlipPublic]:
    return [slip_public(slip) for slip in list_slips(db, user)]


@router.post("/slips", response_model=SlipCreated, status_code=201)
def post_slip(
    payload: SlipCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_issue_roles),
) -> SlipCreated:
    slip, warnings = _run(
        lambda: create_slip(db, payload, user, core_policy=get_settings().consumable_core_policy)
    )
    return SlipCreated(slip=slip_public(slip), core_warnings=warnings)


@router.get("/slips/{slip_id}", response_model=SlipPublic)
def get_slip(
    slip_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SlipPublic:
    slip = _run(lambda: require_slip(db, user, slip_id))
    return slip_public(slip)


@router.post("/slips/{slip_id}/lines/{line_id}/returns", response_model=SlipPublic)
def post_return(
    slip_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: ReturnCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SlipPublic:
    slip = _run(lambda: return_material(db, user, slip_id, line_id, payload))
    return slip_public(slip)


@router.post("/slips/{slip_id}/lines/{line_id}/close", response_model=SlipPublic)
def post_close(
    slip_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: CloseLineIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SlipPublic:
    slip = _run(lambda: close_line(db, user, slip_id, line_id, payload))
    return slip_public(slip)


@router.post("/slips/{slip_id}/lines/{line_id}/core-return", response_model=SlipPublic)
def post_core(
    slip_id: uuid.UUID,
    line_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SlipPublic:
    slip = _run(lambda: return_core(db, user, slip_id, line_id))
    return slip_public(slip)


@router.post("/slips/{slip_id}/confirm", response_model=SlipPublic)
def post_confirm(
    slip_id: uuid.UUID,
    payload: ConfirmSlipIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SlipPublic:
    slip = _run(lambda: confirm_slip(db, user, slip_id, payload))
    return slip_public(slip)


@router.get("/reports/leakage", response_model=LeakageReport)
def get_leakage(
    month: str,
    db: Session = Depends(get_db),
    _user: User = Depends(_report_roles),
) -> LeakageReport:
    return _run(lambda: leakage_report(db, month))


@router.get("/reports/daily", response_model=DailySheet)
def get_daily(
    month: str,
    db: Session = Depends(get_db),
    _user: User = Depends(_report_roles),
) -> DailySheet:
    return _run(lambda: daily_sheet(db, month))


def _daily_table(sheet: DailySheet) -> tuple[list[str], list[list[object]]]:
    headers = [
        "Item Name",
        "Item Group",
        "Party Name",
        "Party Address",
        "Contact No.",
        "Lead Time days",
        "Min Stock",
        "Max Stock",
        "Rate",
        "Op. Stock",
        "Measurement",
    ]
    for day in range(1, sheet.days_in_month + 1):
        headers.append(f"{day} In")
        headers.append(f"{day} Cons")
    headers.extend(["Month In", "Month Cons", "Closing"])
    body: list[list[object]] = []
    for row in sheet.rows:
        values: list[object] = [
            row.item_name,
            row.item_group,
            row.party_name or "",
            row.party_address or "",
            row.contact_no or "",
            row.lead_time_days if row.lead_time_days is not None else "",
            row.min_stock,
            row.max_stock if row.max_stock is not None else "",
            row.rate,
            row.opening_stock,
            row.unit,
        ]
        for day in row.days:
            values.append(day.inward)
            values.append(day.consumption)
        values.extend([row.month_inward, row.month_consumption, row.closing_stock])
        body.append(values)
    return headers, body


def _leakage_table(report: LeakageReport) -> tuple[list[str], list[list[object]]]:
    headers = ["Month", "Level", "Name", "Leakage qty", "Leakage INR", "Variance %"]
    body: list[list[object]] = []
    for level, rows in (
        ("item", report.by_item),
        ("machine", report.by_machine),
        ("operator", report.by_operator),
    ):
        for row in rows:
            body.append([report.month, level, row.label, row.qty, row.value_inr, row.variance_pct if row.variance_pct is not None else ""])
    for row in report.by_month:
        body.append([row.month, "month", row.month, row.qty, row.value_inr, ""])
    return headers, body


def _csv_bytes(headers: list[str], body: list[list[object]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(body)
    return buffer.getvalue().encode("utf-8-sig")


def _xlsx_bytes(title: str, headers: list[str], body: list[list[object]], extra: tuple[str, list[str], list[list[object]]] | None = None) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = title[:31]
    sheet.append(headers)
    for row in body:
        sheet.append(row)
    if extra is not None:
        name, extra_headers, extra_body = extra
        other = book.create_sheet(name[:31])
        other.append(extra_headers)
        for row in extra_body:
            other.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


@router.get("/reports/export")
def export_report(
    month: str,
    kind: Literal["daily", "leakage"] = "daily",
    format: Literal["csv", "xlsx"] = Query(default="csv", alias="format"),
    db: Session = Depends(get_db),
    _user: User = Depends(_report_roles),
) -> Response:
    if kind == "daily":
        sheet = _run(lambda: daily_sheet(db, month))
        headers, body = _daily_table(sheet)
        filename = f"consumables-daily-{month}"
        title = "Daily consumption"
        extra = None
    else:
        report = _run(lambda: leakage_report(db, month))
        headers, body = _leakage_table(report)
        for row in report.stale_slips:
            body.append(
                [
                    report.month,
                    "open slip",
                    f"{row.financial_year}/{row.slip_no_label} {row.machine_name} / {row.received_by_name}",
                    "",
                    "",
                    "",
                ]
            )
        filename = f"consumables-leakage-{month}"
        title = "Leakage"
        stale_headers = ["FY", "Slip", "Date", "Shift", "Department", "Machine", "Operator", "Issued by"]
        stale_body = [
            [
                row.financial_year,
                row.slip_no_label,
                row.slip_date.isoformat(),
                row.shift,
                row.department,
                row.machine_name,
                row.received_by_name,
                row.issued_by_name,
            ]
            for row in report.stale_slips
        ]
        extra = ("Open slips", stale_headers, stale_body)
    if format == "csv":
        content = _csv_bytes(headers, body)
        media = "text/csv"
        suffix = "csv"
    else:
        content = _xlsx_bytes(title, headers, body, extra if kind == "leakage" else None)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        suffix = "xlsx"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}.{suffix}"'},
    )
