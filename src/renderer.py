# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Rich terminal renderer for review reports."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.models import ReviewReport, Severity

_SEVERITY_STYLES: dict[Severity, str] = {
    Severity.CRITICAL: "bold white on red",
    Severity.HIGH: "bold red",
    Severity.MEDIUM: "yellow",
    Severity.LOW: "cyan",
    Severity.INFO: "dim",
}

_SEVERITY_EMOJI: dict[Severity, str] = {
    Severity.CRITICAL: "[!!!]",
    Severity.HIGH: "[!!]",
    Severity.MEDIUM: "[!]",
    Severity.LOW: "[~]",
    Severity.INFO: "[i]",
}


def render_report(report: ReviewReport, console: Console | None = None) -> None:
    """Render a full review report to the terminal with Rich.

    Args:
        report: The completed review report.
        console: Optional Rich Console instance (created if None).
    """
    if console is None:
        console = Console()

    _render_header(report, console)
    _render_summary_table(report, console)

    if report.findings:
        _render_findings(report, console)
    else:
        console.print(
            Panel("[bold green]No findings -- code looks clean![/]", border_style="green")
        )

    _render_footer(report, console)


def _render_header(report: ReviewReport, console: Console) -> None:
    """Print the report header."""
    console.print()
    console.print(
        Panel(
            "[bold]Multi-Agent Code Review Report[/]",
            subtitle=f"Profile: {report.request.profile.value}",
            border_style="blue",
        )
    )


def _render_summary_table(report: ReviewReport, console: Console) -> None:
    """Print a summary statistics table."""
    table = Table(title="Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Files analyzed", str(report.files_analyzed))
    table.add_row("Total findings", str(report.total_findings))
    table.add_row("Duration", f"{report.duration_seconds:.3f}s")

    # Severity breakdown
    for sev in Severity:
        count = report.findings_by_severity.get(sev.value, 0)
        if count > 0:
            style = _SEVERITY_STYLES[sev]
            table.add_row(
                f"  {sev.value.capitalize()}", Text(str(count), style=style)
            )

    # Agent breakdown
    for agent_name, count in sorted(report.findings_by_agent.items()):
        table.add_row(f"  {agent_name.capitalize()} agent", str(count))

    console.print(table)


def _render_findings(report: ReviewReport, console: Console) -> None:
    """Print each finding as a styled panel."""
    console.print()
    console.print("[bold underline]Findings[/]")
    console.print()

    for finding in report.sorted_findings():
        style = _SEVERITY_STYLES[finding.severity]
        marker = _SEVERITY_EMOJI[finding.severity]

        loc = finding.file_path
        if finding.line_number:
            loc += f":{finding.line_number}"
            if finding.end_line:
                loc += f"-{finding.end_line}"

        title_text = Text(f"{marker} {finding.title}", style=style)
        body_parts: list[str] = [finding.description]
        if finding.suggestion:
            body_parts.append(f"\n[bold]Suggestion:[/] {finding.suggestion}")

        console.print(
            Panel(
                "\n".join(body_parts),
                title=title_text,
                subtitle=f"{finding.agent.value} | {loc}",
                border_style=style.split()[-1] if " " in style else style,
            )
        )


def _render_footer(report: ReviewReport, console: Console) -> None:
    """Print the footer."""
    critical = report.findings_by_severity.get("critical", 0)
    high = report.findings_by_severity.get("high", 0)
    if critical or high:
        console.print(
            f"\n[bold red]Action required: {critical} critical, {high} high severity findings.[/]"
        )
    else:
        console.print("\n[bold green]No critical or high severity findings.[/]")
