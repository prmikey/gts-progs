from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .runner import run_export


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Lenovo NetSuite CSV Builder")
        self.geometry("820x560")
        self.resizable(True, True)

        self.intake_path = tk.StringVar()
        self.query_path = tk.StringVar()
        self.batch_path = tk.StringVar()
        self.output_path = tk.StringVar(value=str(Path.cwd() / "outputs" / "netsuite_import.csv"))
        self.config_path = tk.StringVar(value=str(_default_customer_source()))
        self.customer = tk.StringVar(value="humble")
        self.pickup_date = tk.StringVar()
        self.live_lookup = tk.BooleanVar(value=False)
        self.include_assigned_to = tk.BooleanVar(value=False)
        self.pad_rows = tk.StringVar(value="0")

        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        self._file_row(frame, 0, "Intake workbook", self.intake_path, [("Excel files", "*.xlsx")])
        self._file_row(frame, 1, "Query result", self.query_path, [("Excel files", "*.xlsx")])
        self._file_row(frame, 2, "Batch template", self.batch_path, [("Excel files", "*.xlsx")])
        self._file_row(frame, 3, "Output CSV", self.output_path, [("CSV files", "*.csv")], save=True)
        self._file_row(frame, 4, "Customer source", self.config_path, [("Customer files", "*.xlsx *.xlsm *.json"), ("Excel files", "*.xlsx *.xlsm"), ("JSON files", "*.json")])

        ttk.Label(frame, text="Customer key").grid(row=5, column=0, sticky=tk.W, pady=4)
        ttk.Entry(frame, textvariable=self.customer).grid(row=5, column=1, sticky=tk.EW, pady=4)

        ttk.Label(frame, text="Pickup date override").grid(row=6, column=0, sticky=tk.W, pady=4)
        ttk.Entry(frame, textvariable=self.pickup_date).grid(row=6, column=1, sticky=tk.EW, pady=4)

        ttk.Label(frame, text="Pad blank rows").grid(row=7, column=0, sticky=tk.W, pady=4)
        ttk.Entry(frame, textvariable=self.pad_rows, width=12).grid(row=7, column=1, sticky=tk.W, pady=4)

        ttk.Checkbutton(frame, text="Use Lenovo live lookup for missing values", variable=self.live_lookup).grid(
            row=8, column=1, sticky=tk.W, pady=8
        )
        ttk.Checkbutton(frame, text="Fill Assigned To from customer source", variable=self.include_assigned_to).grid(
            row=9, column=1, sticky=tk.W, pady=4
        )

        ttk.Button(frame, text="Create CSV", command=self._start_run).grid(row=10, column=1, sticky=tk.E, pady=8)

        self.log = scrolledtext.ScrolledText(frame, height=12)
        self.log.grid(row=11, column=0, columnspan=3, sticky=tk.NSEW, pady=(12, 0))
        frame.rowconfigure(11, weight=1)

    def _file_row(self, frame, row: int, label: str, variable: tk.StringVar, filetypes, save: bool = False) -> None:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
        ttk.Entry(frame, textvariable=variable).grid(row=row, column=1, sticky=tk.EW, padx=(8, 8), pady=4)
        command = lambda: self._choose_file(variable, filetypes, save)
        ttk.Button(frame, text="Browse", command=command).grid(row=row, column=2, pady=4)

    def _choose_file(self, variable: tk.StringVar, filetypes, save: bool) -> None:
        if save:
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=filetypes)
        else:
            path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            variable.set(path)

    def _start_run(self) -> None:
        if not self.intake_path.get().strip():
            messagebox.showerror("Missing intake workbook", "Choose an intake workbook first.")
            return
        self.log.delete("1.0", tk.END)
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self) -> None:
        try:
            pad_rows = int(self.pad_rows.get().strip() or "0")
            summary = run_export(
                intake_workbook=self.intake_path.get().strip(),
                output_csv=self.output_path.get().strip(),
                customer_key=self.customer.get().strip(),
                config_path=self.config_path.get().strip(),
                query_result=self.query_path.get().strip() or None,
                batch_template=self.batch_path.get().strip() or None,
                live_lookup=self.live_lookup.get(),
                pickup_date_override=self.pickup_date.get().strip() or None,
                pad_rows=pad_rows,
                include_assigned_to=self.include_assigned_to.get(),
            )
            lines = [
                f"Wrote {summary.exported_count} rows to {summary.output_csv}",
                f"Intake rows read: {summary.intake_count}",
            ]
            if summary.warranty_sources:
                sources = ", ".join(f"{key}={value}" for key, value in sorted(summary.warranty_sources.items()))
                lines.append(f"Warranty sources: {sources}")
            if summary.warnings:
                lines.append("")
                lines.append("Warnings:")
                lines.extend(f"- {warning}" for warning in summary.warnings)
            self._set_log("\n".join(lines))
        except Exception as exc:
            self._set_log(str(exc))
            messagebox.showerror("Export failed", str(exc))

    def _set_log(self, text: str) -> None:
        self.log.after(0, lambda: (self.log.delete("1.0", tk.END), self.log.insert(tk.END, text)))


def main() -> int:
    app = App()
    app.mainloop()
    return 0


def _default_customer_source() -> Path:
    candidates = [
        Path.cwd() / "provided_files" / "GTS BF CSV Template .xlsx",
        Path.cwd() / "config" / "GTS BF CSV Template .xlsx",
        Path.cwd() / "config" / "customers.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


if __name__ == "__main__":
    raise SystemExit(main())
