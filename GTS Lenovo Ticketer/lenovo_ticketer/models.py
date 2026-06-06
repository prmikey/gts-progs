from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class IntakeRecord:
    asset_id: str
    serial: str
    bin_location: str = ""
    pickup_date: object = None
    warranty_expiration: object = None
    model: str = ""
    row_number: int = 0


@dataclass
class WarrantyInfo:
    serial: str
    warranty_end: str = ""
    model: str = ""
    machine_type: str = ""
    subseries: str = ""
    source: str = ""


@dataclass
class CustomerProfile:
    key: str
    company: str
    service_board: str
    customer_name: str
    contact: str
    in_facility_location: str
    device_type: str = "Laptop"
    assigned_to: str = ""


@dataclass
class JobSummary:
    output_csv: Path
    intake_count: int = 0
    exported_count: int = 0
    skipped_count: int = 0
    warranty_sources: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
