from __future__ import annotations

from pathlib import Path

from .excel_io import read_batch_template, read_intake_workbook, read_query_result
from .lenovo_api import LenovoLookupError, LenovoWarrantyClient
from .model_names import normalize_model_name
from .models import JobSummary, WarrantyInfo
from .netsuite import build_netsuite_row, load_customer_profiles, write_netsuite_csv


DEFAULT_MODEL_MAP = {
    "300E-CHROMEBOOK-GEN-3": "Lenovo 300E G3",
    "500E-CHROMEBOOK-GEN-3": "Lenovo 500E G3",
    "LENOVO 300E GEN3": "Lenovo 300E G3",
    "LENOVO 500E GEN3": "Lenovo 500E G3",
}


def run_export(
    intake_workbook: str | Path,
    output_csv: str | Path,
    customer_key: str,
    config_path: str | Path,
    intake_sheet: str = "Inbound_Deployment",
    query_result: str | Path | None = None,
    query_sheet: str = "Result",
    batch_template: str | Path | None = None,
    live_lookup: bool = False,
    pickup_date_override: object = None,
    warranty_code: str = "UWP",
    pad_rows: int = 0,
    include_assigned_to: bool = False,
) -> JobSummary:
    output_csv = Path(output_csv)
    summary = JobSummary(output_csv=output_csv)
    profiles = load_customer_profiles(config_path)
    if customer_key not in profiles:
        known = ", ".join(sorted(profiles))
        raise ValueError(f"Unknown customer profile '{customer_key}'. Available profiles: {known}")
    profile = profiles[customer_key]

    records = read_intake_workbook(intake_workbook, intake_sheet)
    summary.intake_count = len(records)

    warranty_by_serial: dict[str, WarrantyInfo] = {}
    if query_result:
        query_data, warnings = read_query_result(query_result, query_sheet, warranty_code, DEFAULT_MODEL_MAP)
        warranty_by_serial.update(query_data)
        summary.warnings.extend(warnings)

    machine_types: dict[str, str] = {}
    if batch_template:
        machine_types.update(read_batch_template(batch_template))

    client = LenovoWarrantyClient(model_map=DEFAULT_MODEL_MAP) if live_lookup else None
    rows: list[dict[str, str]] = []

    for record in records:
        serial_key = record.serial.strip().upper()
        if not serial_key:
            summary.skipped_count += 1
            summary.warnings.append(f"Row {record.row_number}: skipped because serial is blank.")
            continue

        warranty = warranty_by_serial.get(serial_key)
        if client and (warranty is None or not warranty.warranty_end or not warranty.model):
            try:
                live = client.lookup(serial_key, machine_types.get(serial_key))
                warranty = _merge_warranty(warranty, live)
                warranty_by_serial[serial_key] = warranty
            except LenovoLookupError as exc:
                summary.warnings.append(str(exc))

        row = build_netsuite_row(record, profile, warranty, pickup_date_override, DEFAULT_MODEL_MAP, include_assigned_to)
        rows.append(row)

        source = warranty.source if warranty and warranty.source else "intake-only"
        summary.warranty_sources[source] = summary.warranty_sources.get(source, 0) + 1

        if not row["Pickup Date"]:
            summary.warnings.append(f"{record.serial}: pickup date is blank.")
        if not row["Warranty Expiration"]:
            summary.warnings.append(f"{record.serial}: warranty expiration is blank.")
        if not row["PC Information"]:
            summary.warnings.append(f"{record.serial}: model/PC information is blank.")

    write_netsuite_csv(output_csv, rows, pad_rows)
    summary.exported_count = len(rows)
    return summary


def _merge_warranty(existing: WarrantyInfo | None, live: WarrantyInfo) -> WarrantyInfo:
    if existing is None:
        return live
    return WarrantyInfo(
        serial=existing.serial,
        warranty_end=existing.warranty_end or live.warranty_end,
        model=normalize_model_name(existing.model) or live.model,
        machine_type=existing.machine_type or live.machine_type,
        subseries=existing.subseries or live.subseries,
        source=existing.source if existing.warranty_end and existing.model else live.source,
    )
