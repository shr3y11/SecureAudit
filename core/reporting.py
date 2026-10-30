"""Standalone HTML compliance reporting for SecureAudit.

Reports are generated from stored scan records and written as local HTML files.
All untrusted values are escaped before being inserted into the document.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from core.paths import reports_directory as default_reports_directory
from core.evidence import assess_context


DEFAULT_REPORTS_DIRECTORY: Final[Path] = default_reports_directory()

ALLOWED_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "Pass",
        "Fail",
        "Error",
    }
)


class ReportingError(RuntimeError):
    """Raised when a SecureAudit report cannot be generated reliably."""


def _escape(value: Any) -> str:
    """Return a value escaped for safe inclusion in HTML."""

    if value is None:
        return ""

    return html.escape(
        str(value),
        quote=True,
    )


def _format_percentage(
    value: int | float | None,
) -> str:
    """Return a human-readable percentage value."""

    if value is None:
        return "Not available"

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ReportingError(
            "Percentage values must be numeric or null."
        )

    if not 0 <= value <= 100:
        raise ReportingError(
            "Percentage values must be between 0 and 100."
        )

    return f"{value:.2f}%"


def _safe_filename_component(value: str) -> str:
    """Return a filesystem-safe filename component."""

    cleaned = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        value.strip(),
    )
    cleaned = cleaned.strip(".-_")

    return cleaned or "scan"


def _validate_scan(scan: Mapping[str, Any]) -> None:
    """Validate the minimum stored-scan structure required for reporting."""

    required_fields = (
        "scan_id",
        "hostname",
        "started_at_utc",
        "completed_at_utc",
        "selected_count",
        "passed_count",
        "failed_count",
        "error_count",
        "assessed_count",
        "unassessed_count",
        "compliance_score",
        "coverage_percentage",
        "results",
    )

    for field_name in required_fields:
        if field_name not in scan:
            raise ReportingError(
                f"Stored scan is missing {field_name!r}."
            )

    required_string_fields = (
        "scan_id",
        "hostname",
        "started_at_utc",
        "completed_at_utc",
    )

    for field_name in required_string_fields:
        value = scan[field_name]

        if not isinstance(value, str) or not value.strip():
            raise ReportingError(
                f"Stored scan field {field_name!r} "
                "must be a non-empty string."
            )

    integer_fields = (
        "selected_count",
        "passed_count",
        "failed_count",
        "error_count",
        "assessed_count",
        "unassessed_count",
    )

    for field_name in integer_fields:
        value = scan[field_name]

        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
        ):
            raise ReportingError(
                f"Stored scan field {field_name!r} "
                "must be a non-negative integer."
            )

    selected_count = scan["selected_count"]
    passed_count = scan["passed_count"]
    failed_count = scan["failed_count"]
    error_count = scan["error_count"]
    assessed_count = scan["assessed_count"]
    unassessed_count = scan["unassessed_count"]

    if selected_count != passed_count + failed_count + error_count:
        raise ReportingError(
            "Stored scan result counts are inconsistent."
        )

    if assessed_count != passed_count + failed_count:
        raise ReportingError(
            "Stored scan assessed count is inconsistent."
        )

    if unassessed_count != error_count:
        raise ReportingError(
            "Stored scan unassessed count is inconsistent."
        )

    _format_percentage(scan["compliance_score"])
    _format_percentage(scan["coverage_percentage"])

    results = scan["results"]

    if (
        not isinstance(results, Sequence)
        or isinstance(results, (str, bytes))
    ):
        raise ReportingError(
            "Stored scan results must be a sequence."
        )

    if len(results) != selected_count:
        raise ReportingError(
            "Stored scan selected count does not match result count."
        )

    seen_check_ids: set[str] = set()

    for index, result in enumerate(results):
        if not isinstance(result, Mapping):
            raise ReportingError(
                f"Result at index {index} must be a mapping."
            )

        required_result_fields = (
            "check_id",
            "check_name",
            "expected_value",
            "observed_value",
            "status",
            "evidence",
            "timestamp_utc",
        )

        for field_name in required_result_fields:
            if field_name not in result:
                raise ReportingError(
                    f"Result at index {index} is missing "
                    f"{field_name!r}."
                )

        check_id = result["check_id"]

        if not isinstance(check_id, str) or not check_id.strip():
            raise ReportingError(
                f"Result at index {index} has an invalid check_id."
            )

        if check_id in seen_check_ids:
            raise ReportingError(
                f"Duplicate check ID in report results: {check_id!r}"
            )

        seen_check_ids.add(check_id)

        status = result["status"]

        if status not in ALLOWED_STATUSES:
            raise ReportingError(
                f"Result at index {index} has unsupported status: "
                f"{status!r}"
            )

        error_message = result.get("error_message")

        if error_message is not None and not isinstance(
            error_message,
            str,
        ):
            raise ReportingError(
                f"Result at index {index} has an invalid error_message."
            )

        try:
            json.dumps(
                result["evidence"],
                ensure_ascii=False,
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise ReportingError(
                f"Result at index {index} contains "
                "non-JSON-serializable evidence."
            ) from exc


def _status_class(status: str) -> str:
    """Return the CSS class used for one assessment status."""

    return {
        "Pass": "status-pass",
        "Fail": "status-fail",
        "Error": "status-error",
    }[status]


def _render_evidence(evidence: Any) -> str:
    """Return escaped, formatted JSON evidence."""

    evidence_json = json.dumps(
        evidence,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )

    return _escape(evidence_json)


def _catalog_by_id() -> dict[str, Mapping[str, Any]]:
    """Best-effort catalog lookup for report enrichment.

    Reporting must never fail because the catalog cannot be loaded, so
    any problem yields an empty mapping and the report falls back to the
    stored result fields alone.
    """

    try:
        from core.scanner import load_catalog

        return {check["id"]: check for check in load_catalog().get("checks", [])}
    except Exception:
        return {}


def _needs_administrator(result: Mapping[str, Any], catalog: Mapping[str, Mapping[str, Any]]) -> bool:
    entry = catalog.get(str(result.get("check_id", "")))
    return bool(entry and entry.get("requires_administrator"))


def _status_label(result: Mapping[str, Any], catalog: Mapping[str, Mapping[str, Any]]) -> str:
    """Display label for a result status (permission-aware, item #18).

    An Error on a check that requires administrator rights is not a
    failed control: it is unresolved. The stored status stays "Error"
    (scoring semantics do not change); only the presentation says so.
    """

    status = str(result["status"])
    if status == "Error" and _needs_administrator(result, catalog):
        return "Error — UNRESOLVED (administrator required)"
    return status


def _plain_language_section(scan: Mapping[str, Any], catalog: Mapping[str, Mapping[str, Any]]) -> str:
    """Plain-language summary of what needs attention (item #17).

    Written for a non-specialist reader (for example a faculty reviewer):
    for every check that did not pass, what happened, why it matters and
    how to fix it — taken from the catalog's own description and
    remediation text, never invented here.
    """

    cards = []
    for result in scan["results"]:
        if result["status"] == "Pass":
            continue
        entry = catalog.get(str(result.get("check_id", "")), {})
        name = entry.get("name") or result["check_name"]
        if result["status"] == "Error" and _needs_administrator(result, catalog):
            happened = (
                "SecureAudit could not complete this check because it needs "
                "administrator rights. This result is unresolved: it does not "
                "mean the setting is wrong, only that it was not verified."
            )
            fix = "Run SecureAudit as Administrator and scan again so this check can be verified."
        elif result["status"] == "Error":
            happened = (
                "SecureAudit could not complete this check"
                + (f": {result['error_message']}" if result.get("error_message") else ".")
                + " This result is unresolved, not a failure."
            )
            fix = entry.get("remediation") or "Re-run the scan; if the error persists, inspect the technical evidence below."
        else:
            happened = f"Expected: {result['expected_value']}. Found: {result['observed_value']}."
            fix = entry.get("remediation") or "See the technical evidence below for remediation details."
        why = entry.get("description") or ""
        severity = entry.get("severity") or ""
        cards.append(f"""
        <article class="result-card">
            <h3>{_escape(name)}</h3>
            <p><strong>What happened:</strong> {_escape(happened)}</p>
            {f'<p><strong>Why it matters:</strong> {_escape(why)}</p>' if why else ''}
            <p><strong>How to fix it:</strong> {_escape(fix)}</p>
            {f'<p><strong>Severity:</strong> {_escape(severity)}</p>' if severity else ''}
        </article>
        """)

    if not cards:
        return """
        <section aria-label="Plain language summary">
            <h2 class="section-heading">What this means, in plain language</h2>
            <p>Every check that ran passed. Nothing needs attention.</p>
        </section>
        """
    return f"""
        <section aria-label="Plain language summary">
            <h2 class="section-heading">What this means, in plain language</h2>
            <p>These checks did not pass. Each one says what happened, why it
            matters, and how to fix it. The full technical evidence follows below.</p>
            {''.join(cards)}
        </section>
        """


def _render_result(
    result: Mapping[str, Any],
    catalog: Mapping[str, Mapping[str, Any]] | None = None,
) -> str:
    """Render one scanner result as an HTML section."""

    if catalog is None:
        catalog = _catalog_by_id()
    status = str(result["status"])
    error_message = result.get("error_message")

    error_section = ""

    if error_message:
        error_section = f"""
        <div class="error-message">
            <strong>Assessment error:</strong>
            {_escape(error_message)}
        </div>
        """

    return f"""
    <article class="result-card">
        <div class="result-header">
            <div>
                <h3>{_escape(result["check_name"])}</h3>
                <p class="check-id">{_escape(result["check_id"])}</p>
            </div>
            <span class="status-badge {_status_class(status)}">
                {_escape(_status_label(result, catalog))}
            </span>
        </div>

        <dl class="result-details">
            <div>
                <dt>Expected value</dt>
                <dd>{_escape(result["expected_value"])}</dd>
            </div>
            <div>
                <dt>Observed value</dt>
                <dd>{_escape(result["observed_value"])}</dd>
            </div>
            <div>
                <dt>Assessment timestamp</dt>
                <dd>{_escape(result["timestamp_utc"])}</dd>
            </div>
        </dl>

        {error_section}

        <details>
            <summary>View technical evidence</summary>
            <pre>{_render_evidence(result["evidence"])}</pre>
        </details>
    </article>
    """


def build_html_report(
    scan: Mapping[str, Any],
    *,
    previous_scan: Mapping[str, Any] | None = None,
) -> str:
    """Build and return a standalone HTML report for one stored scan.

    When ``previous_scan`` is given, the report gains a "Changes since
    previous scan" section computed by :mod:`core.scan_diff`, including
    both scans' context snapshots when they have them.
    """

    if not isinstance(scan, Mapping):
        raise ReportingError(
            "Stored scan must be provided as a mapping."
        )

    _validate_scan(scan)

    catalog = _catalog_by_id()
    plain_language_html = _plain_language_section(scan, catalog)

    diff_html = ""
    if previous_scan is not None:
        from core.scan_diff import diff_scans

        try:
            diff = diff_scans(previous_scan, scan)
        except ValueError as exc:
            raise ReportingError(f"Invalid previous scan for diff: {exc}") from exc
        rows = "\n".join(
            f"<tr><td>{_escape(t['check_id'])}</td><td>{_escape(t['before'] or '—')}</td>"
            f"<td>{_escape(t['after'] or '—')}</td><td>{_escape(t['change'])}</td></tr>"
            for t in diff["transitions"] if t["change"] != "unchanged"
        ) or '<tr><td colspan="4">No check changed status.</td></tr>'
        counts = diff["counts"]
        diff_html = f"""
        <section class="disclaimer" aria-label="Changes since previous scan">
            <h2>Changes since previous scan</h2>
            <p>Fixed: {counts['fixed']} · Regressed: {counts['regressed']} ·
            Changed: {counts['changed']} · Added: {counts['added']} ·
            Removed: {counts['removed']} · Unchanged: {counts['unchanged']}.</p>
            <table>
                <tr><th>Check</th><th>Before</th><th>After</th><th>Change</th></tr>
                {rows}
            </table>
        </section>
        """

    evidence_html = ""
    if "evidence_context" in scan:
        try:
            evidence = assess_context(scan["evidence_context"], scan["results"])
        except (ValueError, TypeError) as exc:
            raise ReportingError(f"Invalid evidence context: {exc}") from exc
        omitted = ", ".join(cid for cid, state in evidence["states"].items() if state == "O") or "None"
        evidence_html = f"""
        <section class="disclaimer" aria-label="Baseline evidence completeness">
            <h2>Baseline evidence completeness</h2>
            <p>Baseline coverage: {_format_percentage(evidence['baseline_coverage'])}
            ({evidence['baseline_count']} required checks).</p>
            <p>Possible complete-baseline pass fraction:
            {_format_percentage(evidence['lower_bound'])} to {_format_percentage(evidence['upper_bound'])}.</p>
            <p>Aggregate threshold: {_format_percentage(evidence['threshold_percentage'])}.
            Decision: <strong>{_escape(evidence['decision'])}</strong>.</p>
            <p>Omitted required checks: {_escape(omitted)}.</p>
            <p>Baseline version: {_escape(evidence['baseline_version'])}.
            Decision version: {_escape(evidence['decision_version'])}.
            Catalog SHA-256: {_escape(evidence['catalog_sha256'])}.</p>
            <p>ABOVE means every permitted completion meets the aggregate threshold.
            BELOW means every completion falls below it. UNRESOLVED means missing
            evidence could change that conclusion. Bounds assume correct Pass/Fail
            readings. Mandatory controls require separate review.</p>
        </section>
        """

    results_html = "\n".join(
        _render_result(result, catalog)
        for result in scan["results"]
    )

    if not results_html:
        results_html = """
        <div class="empty-state">
            No checks were selected for this scan.
        </div>
        """

    compliance_score = _format_percentage(
        scan["compliance_score"]
    )
    coverage_percentage = _format_percentage(
        scan["coverage_percentage"]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >
    <title>SecureAudit Report - {_escape(scan["hostname"])}</title>

    <style>
        :root {{
            color-scheme: light;
            font-family:
                Inter,
                "Segoe UI",
                Arial,
                sans-serif;
            background: #f4f6f8;
            color: #17212b;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            background: #f4f6f8;
            color: #17212b;
        }}

        .page {{
            width: min(1120px, calc(100% - 32px));
            margin: 32px auto;
        }}

        .report-header {{
            padding: 28px;
            border-radius: 14px;
            background: #17212b;
            color: #ffffff;
        }}

        .report-header h1 {{
            margin: 0 0 8px;
            font-size: 30px;
        }}

        .report-header p {{
            margin: 4px 0;
            color: #d8e0e7;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(150px, 1fr));
            gap: 14px;
            margin: 20px 0;
        }}

        .summary-card {{
            padding: 18px;
            border: 1px solid #dde3e8;
            border-radius: 12px;
            background: #ffffff;
            box-shadow: 0 3px 10px rgba(23, 33, 43, 0.05);
        }}

        .summary-card .label {{
            margin-bottom: 8px;
            color: #53606d;
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        .summary-card .value {{
            font-size: 26px;
            font-weight: 700;
        }}

        .section-heading {{
            margin: 30px 0 14px;
        }}

        .result-card {{
            margin-bottom: 16px;
            padding: 20px;
            border: 1px solid #dde3e8;
            border-radius: 12px;
            background: #ffffff;
        }}

        .result-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
        }}

        .result-header h3 {{
            margin: 0;
            font-size: 19px;
        }}

        .check-id {{
            margin: 5px 0 0;
            color: #687684;
            font-family: Consolas, monospace;
            font-size: 13px;
        }}

        .status-badge {{
            display: inline-block;
            min-width: 70px;
            padding: 7px 12px;
            border-radius: 999px;
            text-align: center;
            font-size: 13px;
            font-weight: 700;
        }}

        .status-pass {{
            background: #dff5e7;
            color: #176536;
        }}

        .status-fail {{
            background: #fde5e5;
            color: #9f2424;
        }}

        .status-error {{
            background: #fff0d5;
            color: #8a5200;
        }}

        .result-details {{
            display: grid;
            gap: 12px;
            margin: 20px 0;
        }}

        .result-details div {{
            display: grid;
            grid-template-columns: 180px 1fr;
            gap: 16px;
        }}

        dt {{
            color: #53606d;
            font-weight: 600;
        }}

        dd {{
            margin: 0;
            overflow-wrap: anywhere;
        }}

        .error-message {{
            margin: 14px 0;
            padding: 12px;
            border-left: 4px solid #d98200;
            background: #fff7e8;
            overflow-wrap: anywhere;
        }}

        details {{
            margin-top: 16px;
        }}

        summary {{
            cursor: pointer;
            font-weight: 600;
        }}

        pre {{
            max-height: 420px;
            padding: 16px;
            overflow: auto;
            border-radius: 8px;
            background: #101820;
            color: #e8eef3;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
        }}

        .empty-state {{
            padding: 28px;
            border: 1px dashed #adb8c2;
            border-radius: 12px;
            background: #ffffff;
            color: #53606d;
            text-align: center;
        }}

        .disclaimer {{
            margin-top: 28px;
            padding: 16px;
            border-radius: 10px;
            background: #eaf0f5;
            color: #44515e;
            font-size: 13px;
            line-height: 1.5;
        }}

        .footer {{
            margin: 24px 0;
            color: #687684;
            font-size: 13px;
            text-align: center;
        }}

        @media (max-width: 640px) {{
            .page {{
                width: min(100% - 20px, 1120px);
                margin: 10px auto;
            }}

            .report-header {{
                padding: 20px;
            }}

            .result-header {{
                flex-direction: column;
            }}

            .result-details div {{
                grid-template-columns: 1fr;
                gap: 4px;
            }}
        }}

        @media print {{
            body {{
                background: #ffffff;
            }}

            .page {{
                width: 100%;
                margin: 0;
            }}

            .result-card,
            .summary-card {{
                break-inside: avoid;
                box-shadow: none;
            }}

            details {{
                display: block;
            }}

            details > summary {{
                display: none;
            }}

            details > pre {{
                display: block;
                max-height: none;
            }}
        }}
    </style>
</head>

<body>
    <main class="page">
        <header class="report-header">
            <h1>SecureAudit Compliance Report</h1>
            <p>
                Host:
                <strong>{_escape(scan["hostname"])}</strong>
            </p>
            <p>
                Scan ID:
                <strong>{_escape(scan["scan_id"])}</strong>
            </p>
            <p>
                Started:
                {_escape(scan["started_at_utc"])}
            </p>
            <p>
                Completed:
                {_escape(scan["completed_at_utc"])}
            </p>
        </header>

        <section
            class="summary-grid"
            aria-label="Assessment summary"
        >
            <div class="summary-card">
                <div class="label">Compliance score</div>
                <div class="value">{_escape(compliance_score)}</div>
            </div>

            <div class="summary-card">
                <div class="label">Assessment coverage</div>
                <div class="value">
                    {_escape(coverage_percentage)}
                </div>
            </div>

            <div class="summary-card">
                <div class="label">Selected</div>
                <div class="value">
                    {_escape(scan["selected_count"])}
                </div>
            </div>

            <div class="summary-card">
                <div class="label">Passed</div>
                <div class="value">
                    {_escape(scan["passed_count"])}
                </div>
            </div>

            <div class="summary-card">
                <div class="label">Failed</div>
                <div class="value">
                    {_escape(scan["failed_count"])}
                </div>
            </div>

            <div class="summary-card">
                <div class="label">Errors</div>
                <div class="value">
                    {_escape(scan["error_count"])}
                </div>
            </div>
        </section>

        {evidence_html}
        {diff_html}
        {plain_language_html}

        <h2 class="section-heading">Technical assessment results</h2>

        <section aria-label="Technical assessment results">
            {results_html}
        </section>

        <aside class="disclaimer">
            <strong>Assessment limitation:</strong>
            This report represents a point-in-time technical assessment of
            the selected local Windows controls. It is not a certification,
            audit opinion, or guarantee of complete regulatory compliance.
            Results marked Error were not successfully assessed and are
            excluded from the compliance-score denominator.
        </aside>

        <footer class="footer">
            Generated locally by SecureAudit.
        </footer>
    </main>
</body>
</html>
"""


def write_html_report(
    scan: Mapping[str, Any],
    *,
    output_directory: str | Path = DEFAULT_REPORTS_DIRECTORY,
    filename: str | None = None,
    previous_scan: Mapping[str, Any] | None = None,
) -> Path:
    """Generate a report, write it to disk, and return its path."""

    report_html = build_html_report(scan, previous_scan=previous_scan)

    output_path = Path(output_directory)
    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    if filename is None:
        safe_scan_id = _safe_filename_component(
            str(scan["scan_id"])
        )
        filename = f"secureaudit-{safe_scan_id}.html"
    else:
        if not isinstance(filename, str) or not filename.strip():
            raise ReportingError(
                "Report filename must be a non-empty string."
            )

        filename = Path(filename).name

        if not filename.lower().endswith(".html"):
            filename = f"{filename}.html"

    report_path = output_path / filename

    try:
        report_path.write_text(
            report_html,
            encoding="utf-8",
        )
    except OSError as exc:
        raise ReportingError(
            f"Could not write HTML report: {exc}"
        ) from exc

    return report_path
