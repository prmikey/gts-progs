from __future__ import annotations

import argparse
from pathlib import Path

from .runner import run_export


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a NetSuite break/fix import CSV from an intake workbook and Lenovo warranty data.",
    )
    parser.add_argument("--intake", required=True, help="Path to the intake workbook.")
    parser.add_argument("--output", required=True, help="Path for the NetSuite CSV export.")
    parser.add_argument("--customer", default="humble", help="Customer profile key from config/customers.json.")
    parser.add_argument("--config", default="config/customers.json", help="Customer profile JSON file or NetSuite template workbook.")
    parser.add_argument("--intake-sheet", default="Inbound_Deployment", help="Intake sheet name.")
    parser.add_argument("--query-result", help="Lenovo Query Result.xlsx path.")
    parser.add_argument("--query-sheet", default="Result", help="Lenovo query result sheet name.")
    parser.add_argument("--batch-template", help="Warranty batch template path for serial to machine type mapping.")
    parser.add_argument("--live-lookup", action="store_true", help="Use Lenovo live web lookup for missing warranty/model values.")
    parser.add_argument("--pickup-date", help="Override pickup date for rows where the intake date is blank, for example 6/2/2026.")
    parser.add_argument("--warranty-code", default="UWP", help="Preferred Lenovo entitlement code in Query Result.xlsx.")
    parser.add_argument("--pad-rows", type=int, default=0, help="Pad CSV with blank rows up to this many data rows.")
    parser.add_argument("--include-assigned-to", action="store_true", help="Fill Assigned To from Template Data when available.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    summary = run_export(
        intake_workbook=Path(args.intake),
        output_csv=Path(args.output),
        customer_key=args.customer,
        config_path=Path(args.config),
        intake_sheet=args.intake_sheet,
        query_result=Path(args.query_result) if args.query_result else None,
        query_sheet=args.query_sheet,
        batch_template=Path(args.batch_template) if args.batch_template else None,
        live_lookup=args.live_lookup,
        pickup_date_override=args.pickup_date,
        warranty_code=args.warranty_code,
        pad_rows=args.pad_rows,
        include_assigned_to=args.include_assigned_to,
    )

    print(f"Wrote {summary.exported_count} rows to {summary.output_csv}")
    if summary.warranty_sources:
        sources = ", ".join(f"{key}={value}" for key, value in sorted(summary.warranty_sources.items()))
        print(f"Warranty sources: {sources}")
    if summary.warnings:
        print("Warnings:")
        for warning in summary.warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
