"""SecureAudit Windows desktop application.

This module provides the application orchestration layer and the Tkinter
presentation layer for the local SecureAudit Windows MVP.

Security-sensitive scanner execution, scoring, persistence, and report
generation remain delegated to the reusable core modules.
"""

from __future__ import annotations

import os
import socket
import tkinter as tk
from datetime import UTC, datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Iterable

from core.database import get_scan, list_scans, save_scan
from core.reporting import write_html_report
from core.scanner import load_catalog, run_check
from core.scoring import calculate_score


class ScanWorkflowError(RuntimeError):
    """Raised when the complete local scan workflow cannot be completed."""


def _utc_now() -> str:
    """Return the current UTC time as a timezone-aware ISO 8601 string."""

    return datetime.now(UTC).isoformat()


def _validate_selected_check_ids(
    selected_check_ids: Iterable[str],
) -> list[str]:
    """Validate application-level structure for selected check identifiers."""

    if isinstance(selected_check_ids, (str, bytes)):
        raise ValueError(
            "selected_check_ids must be an iterable of check IDs, "
            "not a single string."
        )

    check_ids = list(selected_check_ids)

    if not check_ids:
        raise ValueError("At least one check must be selected.")

    for check_id in check_ids:
        if not isinstance(check_id, str):
            raise ValueError("Every selected check ID must be a string.")

        if not check_id.strip():
            raise ValueError("Selected check IDs cannot be empty.")

    if len(check_ids) != len(set(check_ids)):
        raise ValueError("Duplicate check IDs are not allowed.")

    return check_ids


def run_local_scan(
    selected_check_ids: Iterable[str],
) -> dict[str, Any]:
    """Run the complete local SecureAudit assessment workflow."""

    check_ids = _validate_selected_check_ids(selected_check_ids)

    hostname = socket.gethostname()
    started_at_utc = _utc_now()

    results: list[dict[str, Any]] = []

    for check_id in check_ids:
        result = run_check(check_id)
        results.append(result)

    completed_at_utc = _utc_now()

    summary = calculate_score(results)

    scan_id = save_scan(
        hostname=hostname,
        results=results,
        summary=summary,
        started_at_utc=started_at_utc,
        completed_at_utc=completed_at_utc,
    )

    stored_scan = get_scan(scan_id)

    if stored_scan is None:
        raise ScanWorkflowError(
            f"Scan {scan_id!r} was saved but could not be read back "
            "from the database."
        )

    report_path = write_html_report(stored_scan)

    return {
        "scan_id": scan_id,
        "scan": stored_scan,
        "report_path": Path(report_path),
    }


def _load_enabled_checks() -> list[dict[str, Any]]:
    """Load enabled approved checks for display in the desktop interface."""

    catalog = load_catalog()
    checks = catalog.get("checks")

    if not isinstance(checks, list):
        raise ScanWorkflowError(
            "The approved check catalog does not contain a valid checks list."
        )

    enabled_checks: list[dict[str, Any]] = []

    for check in checks:
        if not isinstance(check, dict):
            raise ScanWorkflowError(
                "The approved check catalog contains an invalid check entry."
            )

        if check.get("enabled") is True:
            enabled_checks.append(check)

    if not enabled_checks:
        raise ScanWorkflowError(
            "The approved check catalog contains no enabled checks."
        )

    return enabled_checks


class SecureAuditApp:
    """Tkinter desktop interface for the SecureAudit Windows MVP."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SecureAudit")
        self.root.geometry("1150x800")
        self.root.minsize(920, 680)

        self.check_variables: dict[str, tk.BooleanVar] = {}

        self.selection_status = tk.StringVar(value="0 checks selected")

        self.passed_value = tk.StringVar(value="0")
        self.failed_value = tk.StringVar(value="0")
        self.error_value = tk.StringVar(value="0")
        self.score_value = tk.StringVar(value="—")
        self.coverage_value = tk.StringVar(value="—")

        self.last_report_path: Path | None = None
        self.current_scan_id: str | None = None

        self._build_interface()

    def _build_interface(self) -> None:
        """Create the main application interface."""

        main_frame = ttk.Frame(
            self.root,
            padding=20,
        )
        main_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        title_label = ttk.Label(
            main_frame,
            text="SecureAudit",
            font=("Segoe UI", 22, "bold"),
        )
        title_label.pack(anchor=tk.W)

        subtitle_label = ttk.Label(
            main_frame,
            text="Windows Technical Configuration Assessment",
            font=("Segoe UI", 11),
        )
        subtitle_label.pack(
            anchor=tk.W,
            pady=(0, 14),
        )

        information_label = ttk.Label(
            main_frame,
            text=(
                "Select approved technical checks to assess this Windows "
                "system. Only predefined SecureAudit scanner modules can run."
            ),
            wraplength=1050,
            justify=tk.LEFT,
        )
        information_label.pack(
            anchor=tk.W,
            pady=(0, 12),
        )

        navigation_frame = ttk.Frame(main_frame)
        navigation_frame.pack(
            fill=tk.X,
            pady=(0, 10),
        )

        history_button = ttk.Button(
            navigation_frame,
            text="Scan History",
            command=self._open_scan_history,
        )
        history_button.pack(side=tk.RIGHT)

        self.open_report_button = ttk.Button(
            navigation_frame,
            text="Open HTML Report",
            command=self._open_current_report,
            state=tk.DISABLED,
        )
        self.open_report_button.pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )

        content_pane = ttk.Panedwindow(
            main_frame,
            orient=tk.VERTICAL,
        )
        content_pane.pack(
            fill=tk.BOTH,
            expand=True,
        )

        checklist_section = ttk.Frame(
            content_pane,
            padding=(0, 0, 0, 10),
        )

        results_section = ttk.Frame(
            content_pane,
            padding=(0, 10, 0, 0),
        )

        content_pane.add(
            checklist_section,
            weight=2,
        )

        content_pane.add(
            results_section,
            weight=3,
        )

        self._build_checklist_section(checklist_section)
        self._build_results_section(results_section)

    def _build_checklist_section(
        self,
        parent: ttk.Frame,
    ) -> None:
        """Build the approved-check selection area."""

        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.pack(
            fill=tk.X,
            pady=(0, 10),
        )

        select_all_button = ttk.Button(
            toolbar_frame,
            text="Select All",
            command=self._select_all_checks,
        )
        select_all_button.pack(side=tk.LEFT)

        clear_all_button = ttk.Button(
            toolbar_frame,
            text="Clear All",
            command=self._clear_all_checks,
        )
        clear_all_button.pack(
            side=tk.LEFT,
            padx=(8, 0),
        )

        selection_label = ttk.Label(
            toolbar_frame,
            textvariable=self.selection_status,
        )
        selection_label.pack(side=tk.RIGHT)

        checklist_container = ttk.Frame(parent)
        checklist_container.pack(
            fill=tk.BOTH,
            expand=True,
        )

        canvas = tk.Canvas(
            checklist_container,
            highlightthickness=0,
        )

        scrollbar = ttk.Scrollbar(
            checklist_container,
            orient=tk.VERTICAL,
            command=canvas.yview,
        )

        self.checklist_frame = ttk.Frame(canvas)

        self.checklist_frame.bind(
            "<Configure>",
            lambda event: canvas.configure(
                scrollregion=canvas.bbox("all")
            ),
        )

        canvas_window = canvas.create_window(
            (0, 0),
            window=self.checklist_frame,
            anchor=tk.NW,
        )

        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(
                canvas_window,
                width=event.width,
            ),
        )

        canvas.configure(
            yscrollcommand=scrollbar.set,
        )

        canvas.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
        )

        scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y,
        )

        self._populate_checklist()

        controls_frame = ttk.Frame(parent)
        controls_frame.pack(
            fill=tk.X,
            pady=(10, 0),
        )

        self.run_button = ttk.Button(
            controls_frame,
            text="Run Selected Checks",
            command=self._run_selected_checks,
        )
        self.run_button.pack(side=tk.RIGHT)

    def _build_results_section(
        self,
        parent: ttk.Frame,
    ) -> None:
        """Build scan summary and detailed result table."""

        heading = ttk.Label(
            parent,
            text="Latest Scan Results",
            font=("Segoe UI", 14, "bold"),
        )
        heading.pack(
            anchor=tk.W,
            pady=(0, 10),
        )

        summary_frame = ttk.Frame(parent)
        summary_frame.pack(
            fill=tk.X,
            pady=(0, 12),
        )

        summary_items = [
            ("Passed", self.passed_value),
            ("Failed", self.failed_value),
            ("Errors", self.error_value),
            ("Compliance Score", self.score_value),
            ("Assessment Coverage", self.coverage_value),
        ]

        for column, (label_text, value_variable) in enumerate(
            summary_items
        ):
            summary_frame.columnconfigure(
                column,
                weight=1,
            )

            card = ttk.LabelFrame(
                summary_frame,
                text=label_text,
                padding=10,
            )
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 5, 5),
            )

            value_label = ttk.Label(
                card,
                textvariable=value_variable,
                font=("Segoe UI", 13, "bold"),
            )
            value_label.pack()

        table_frame = ttk.Frame(parent)
        table_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        columns = (
            "check_id",
            "check_name",
            "status",
            "expected",
            "observed",
        )

        self.results_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=10,
        )

        headings = {
            "check_id": "Check ID",
            "check_name": "Check",
            "status": "Status",
            "expected": "Expected",
            "observed": "Observed",
        }

        for column, heading in headings.items():
            self.results_table.heading(
                column,
                text=heading,
            )

        self.results_table.column(
            "check_id",
            width=120,
            anchor=tk.W,
        )
        self.results_table.column(
            "check_name",
            width=210,
            anchor=tk.W,
        )
        self.results_table.column(
            "status",
            width=80,
            anchor=tk.CENTER,
        )
        self.results_table.column(
            "expected",
            width=280,
            anchor=tk.W,
        )
        self.results_table.column(
            "observed",
            width=300,
            anchor=tk.W,
        )

        vertical_scrollbar = ttk.Scrollbar(
            table_frame,
            orient=tk.VERTICAL,
            command=self.results_table.yview,
        )

        horizontal_scrollbar = ttk.Scrollbar(
            table_frame,
            orient=tk.HORIZONTAL,
            command=self.results_table.xview,
        )

        self.results_table.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        self.results_table.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        vertical_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        horizontal_scrollbar.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        table_frame.rowconfigure(
            0,
            weight=1,
        )
        table_frame.columnconfigure(
            0,
            weight=1,
        )

        self.report_status = ttk.Label(
            parent,
            text="No report selected in this session.",
        )
        self.report_status.pack(
            anchor=tk.W,
            pady=(8, 0),
        )

    def _populate_checklist(self) -> None:
        """Load enabled checks from the approved catalog."""

        try:
            checks = _load_enabled_checks()
        except Exception as exc:
            messagebox.showerror(
                "Catalog Error",
                (
                    "SecureAudit could not load the approved "
                    f"check catalog.\n\n{exc}"
                ),
            )
            self.root.after(
                0,
                self.root.destroy,
            )
            return

        for check in checks:
            check_id = check["id"]
            check_name = check["name"]

            variable = tk.BooleanVar(value=False)
            self.check_variables[check_id] = variable

            check_frame = ttk.Frame(
                self.checklist_frame,
                padding=(8, 10),
            )
            check_frame.pack(
                fill=tk.X,
                anchor=tk.W,
            )

            checkbox = ttk.Checkbutton(
                check_frame,
                text=f"{check_name} ({check_id})",
                variable=variable,
                command=self._update_selection_status,
            )
            checkbox.pack(anchor=tk.W)

            metadata_parts = [
                f"Category: {check.get('category', 'Unknown')}",
                f"Severity: {check.get('severity', 'Unknown')}",
            ]

            if check.get("requires_administrator") is True:
                metadata_parts.append("Administrator required")
            else:
                metadata_parts.append(
                    "Administrator not required"
                )

            metadata_label = ttk.Label(
                check_frame,
                text=" | ".join(metadata_parts),
            )
            metadata_label.pack(
                anchor=tk.W,
                padx=(24, 0),
                pady=(3, 0),
            )

            description = check.get("description")

            if description:
                description_label = ttk.Label(
                    check_frame,
                    text=str(description),
                    wraplength=900,
                    justify=tk.LEFT,
                )
                description_label.pack(
                    anchor=tk.W,
                    padx=(24, 0),
                    pady=(3, 0),
                )

            separator = ttk.Separator(
                self.checklist_frame,
                orient=tk.HORIZONTAL,
            )
            separator.pack(fill=tk.X)

        self._update_selection_status()

    def _selected_check_ids(self) -> list[str]:
        """Return the check IDs currently selected in the GUI."""

        return [
            check_id
            for check_id, variable in self.check_variables.items()
            if variable.get()
        ]

    def _update_selection_status(self) -> None:
        """Update the selected-check counter."""

        selected_count = len(
            self._selected_check_ids()
        )

        if selected_count == 1:
            text = "1 check selected"
        else:
            text = f"{selected_count} checks selected"

        self.selection_status.set(text)

    def _select_all_checks(self) -> None:
        """Select every enabled catalog check."""

        for variable in self.check_variables.values():
            variable.set(True)

        self._update_selection_status()

    def _clear_all_checks(self) -> None:
        """Clear every selected catalog check."""

        for variable in self.check_variables.values():
            variable.set(False)

        self._update_selection_status()

    def _clear_results_table(self) -> None:
        """Remove previous result rows."""

        for item in self.results_table.get_children():
            self.results_table.delete(item)

    def _display_scan_results(
        self,
        scan: dict[str, Any],
        report_path: Path | None = None,
    ) -> None:
        """Display a persisted scan in the main window."""

        self._clear_results_table()

        self.current_scan_id = scan["scan_id"]

        self.passed_value.set(
            str(scan["passed_count"])
        )
        self.failed_value.set(
            str(scan["failed_count"])
        )
        self.error_value.set(
            str(scan["error_count"])
        )

        compliance_score = scan["compliance_score"]

        if compliance_score is None:
            self.score_value.set(
                "Not available"
            )
        else:
            self.score_value.set(
                f"{compliance_score:.2f}%"
            )

        self.coverage_value.set(
            f"{scan['coverage_percentage']:.2f}%"
        )

        for result in scan["results"]:
            self.results_table.insert(
                "",
                tk.END,
                values=(
                    result["check_id"],
                    result["check_name"],
                    result["status"],
                    result["expected_value"],
                    result["observed_value"],
                ),
            )

        if report_path is not None:
            self.last_report_path = report_path

            self.report_status.configure(
                text=f"Report: {report_path.resolve()}"
            )
        else:
            self.last_report_path = None

            self.report_status.configure(
                text=(
                    "Historical scan loaded. "
                    "Open HTML Report will generate/open its report."
                )
            )

        self.open_report_button.configure(
            state=tk.NORMAL,
        )

    def _run_selected_checks(self) -> None:
        """Run the currently selected approved checks."""

        selected_check_ids = self._selected_check_ids()

        if not selected_check_ids:
            messagebox.showwarning(
                "No Checks Selected",
                "Select at least one approved check before running a scan.",
            )
            return

        self.run_button.configure(
            state=tk.DISABLED,
        )

        self.root.update_idletasks()

        try:
            workflow_result = run_local_scan(
                selected_check_ids
            )
        except Exception as exc:
            messagebox.showerror(
                "Scan Error",
                (
                    "SecureAudit could not complete the scan.\n\n"
                    f"{exc}"
                ),
            )
            return
        finally:
            self.run_button.configure(
                state=tk.NORMAL,
            )

        scan = workflow_result["scan"]
        report_path = workflow_result["report_path"]

        self._display_scan_results(
            scan,
            report_path,
        )

    def _open_scan_history(self) -> None:
        """Open a window containing recent persisted scans."""

        try:
            scans = list_scans(limit=100)
        except Exception as exc:
            messagebox.showerror(
                "Scan History Error",
                f"SecureAudit could not read scan history.\n\n{exc}",
            )
            return

        history_window = tk.Toplevel(self.root)
        history_window.title("SecureAudit Scan History")
        history_window.geometry("900x450")
        history_window.minsize(760, 350)
        history_window.transient(self.root)

        outer_frame = ttk.Frame(
            history_window,
            padding=16,
        )
        outer_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        heading = ttk.Label(
            outer_frame,
            text="Scan History",
            font=("Segoe UI", 16, "bold"),
        )
        heading.pack(
            anchor=tk.W,
            pady=(0, 10),
        )

        if not scans:
            empty_label = ttk.Label(
                outer_frame,
                text="No completed scans are stored yet.",
            )
            empty_label.pack(
                anchor=tk.W,
            )
            return

        table_frame = ttk.Frame(outer_frame)
        table_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        columns = (
            "completed",
            "hostname",
            "selected",
            "passed",
            "failed",
            "errors",
            "score",
            "coverage",
        )

        history_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "completed": "Completed",
            "hostname": "Hostname",
            "selected": "Selected",
            "passed": "Passed",
            "failed": "Failed",
            "errors": "Errors",
            "score": "Score",
            "coverage": "Coverage",
        }

        for column, heading_text in headings.items():
            history_table.heading(
                column,
                text=heading_text,
            )

        history_table.column(
            "completed",
            width=180,
        )
        history_table.column(
            "hostname",
            width=130,
        )
        history_table.column(
            "selected",
            width=70,
            anchor=tk.CENTER,
        )
        history_table.column(
            "passed",
            width=65,
            anchor=tk.CENTER,
        )
        history_table.column(
            "failed",
            width=65,
            anchor=tk.CENTER,
        )
        history_table.column(
            "errors",
            width=65,
            anchor=tk.CENTER,
        )
        history_table.column(
            "score",
            width=90,
            anchor=tk.CENTER,
        )
        history_table.column(
            "coverage",
            width=90,
            anchor=tk.CENTER,
        )

        history_scrollbar = ttk.Scrollbar(
            table_frame,
            orient=tk.VERTICAL,
            command=history_table.yview,
        )

        history_table.configure(
            yscrollcommand=history_scrollbar.set,
        )

        history_table.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
        )

        history_scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y,
        )

        for scan in scans:
            score = scan["compliance_score"]

            if score is None:
                score_text = "N/A"
            else:
                score_text = f"{score:.2f}%"

            coverage_text = (
                f"{scan['coverage_percentage']:.2f}%"
            )

            history_table.insert(
                "",
                tk.END,
                iid=scan["scan_id"],
                values=(
                    scan["completed_at_utc"],
                    scan["hostname"],
                    scan["selected_count"],
                    scan["passed_count"],
                    scan["failed_count"],
                    scan["error_count"],
                    score_text,
                    coverage_text,
                ),
            )

        controls_frame = ttk.Frame(outer_frame)
        controls_frame.pack(
            fill=tk.X,
            pady=(10, 0),
        )

        def load_selected_scan() -> None:
            selected_items = history_table.selection()

            if not selected_items:
                messagebox.showwarning(
                    "No Scan Selected",
                    "Select a historical scan first.",
                    parent=history_window,
                )
                return

            scan_id = selected_items[0]

            try:
                scan = get_scan(scan_id)
            except Exception as exc:
                messagebox.showerror(
                    "Scan History Error",
                    (
                        "SecureAudit could not load the "
                        f"selected scan.\n\n{exc}"
                    ),
                    parent=history_window,
                )
                return

            if scan is None:
                messagebox.showerror(
                    "Scan History Error",
                    "The selected scan no longer exists.",
                    parent=history_window,
                )
                return

            self._display_scan_results(scan)
            history_window.destroy()

        load_button = ttk.Button(
            controls_frame,
            text="Load Selected Scan",
            command=load_selected_scan,
        )
        load_button.pack(side=tk.RIGHT)

        history_table.bind(
            "<Double-1>",
            lambda event: load_selected_scan(),
        )

    def _report_path_for_scan(
        self,
        scan_id: str,
    ) -> Path:
        """Return the standard HTML report path for a scan."""

        return (
            Path("reports")
            / f"secureaudit-{scan_id}.html"
        )

    def _open_current_report(self) -> None:
        """Open or generate the report for the currently displayed scan."""

        if self.current_scan_id is None:
            messagebox.showwarning(
                "No Scan Selected",
                "Run or load a scan before opening a report.",
            )
            return

        report_path = self.last_report_path

        if report_path is None or not report_path.exists():
            standard_report_path = self._report_path_for_scan(
                self.current_scan_id
            )

            if standard_report_path.exists():
                report_path = standard_report_path
            else:
                try:
                    scan = get_scan(
                        self.current_scan_id
                    )
                except Exception as exc:
                    messagebox.showerror(
                        "Report Error",
                        (
                            "SecureAudit could not load the "
                            f"selected scan.\n\n{exc}"
                        ),
                    )
                    return

                if scan is None:
                    messagebox.showerror(
                        "Report Error",
                        "The selected scan no longer exists.",
                    )
                    return

                try:
                    report_path = Path(
                        write_html_report(scan)
                    )
                except Exception as exc:
                    messagebox.showerror(
                        "Report Error",
                        (
                            "SecureAudit could not generate "
                            f"the HTML report.\n\n{exc}"
                        ),
                    )
                    return

        try:
            os.startfile(
                report_path.resolve()
            )
        except OSError as exc:
            messagebox.showerror(
                "Report Error",
                (
                    "Windows could not open the HTML report.\n\n"
                    f"{exc}"
                ),
            )
            return

        self.last_report_path = report_path

        self.report_status.configure(
            text=f"Report: {report_path.resolve()}"
        )


def main() -> None:
    """Launch the SecureAudit desktop application."""

    root = tk.Tk()
    SecureAuditApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()