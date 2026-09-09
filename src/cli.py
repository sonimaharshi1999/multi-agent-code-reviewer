# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""CLI entry point using Click."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from src.agents.orchestrator import OrchestratorAgent
from src.agents.performance_agent import PerformanceAgent
from src.agents.security_agent import SecurityAgent
from src.agents.style_agent import StyleAgent
from src.message_bus import MessageBus
from src.models import ReviewProfile, ReviewRequest
from src.providers.claude_cli import ClaudeCLIProvider
from src.renderer import render_report


def _resolve_files(paths: tuple[str, ...], recursive: bool) -> list[str]:
    """Expand directories and globs into a list of .py file paths.

    Args:
        paths: CLI-supplied paths (files or directories).
        recursive: Whether to walk directories recursively.

    Returns:
        Sorted list of resolved .py file paths.
    """
    files: list[str] = []
    for p in paths:
        path = Path(p)
        if path.is_file() and path.suffix == ".py":
            files.append(str(path.resolve()))
        elif path.is_dir():
            pattern = "**/*.py" if recursive else "*.py"
            files.extend(str(f.resolve()) for f in path.glob(pattern))
    return sorted(set(files))


@click.command()
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    "--profile",
    "-p",
    type=click.Choice(["quick", "standard", "thorough"], case_sensitive=False),
    default="standard",
    help="Review depth profile.",
)
@click.option("--recursive", "-r", is_flag=True, help="Recurse into directories.")
@click.option("--use-llm", is_flag=True, help="Enable LLM-enhanced analysis (requires Claude CLI).")
@click.option("--json-output", "-j", is_flag=True, help="Output report as JSON.")
@click.option("--min-severity", type=click.Choice(["critical", "high", "medium", "low", "info"]), default="info", help="Minimum severity to display.")
def main(
    paths: tuple[str, ...],
    profile: str,
    recursive: bool,
    use_llm: bool,
    json_output: bool,
    min_severity: str,
) -> None:
    """Multi-Agent Code Review System.

    Analyze Python files with specialized agents for security,
    performance, and style issues.

    PATHS can be files or directories containing Python files.
    """
    console = Console(stderr=True)
    files = _resolve_files(paths, recursive)
    if not files:
        console.print("[bold red]No Python files found.[/]")
        sys.exit(1)

    console.print(f"[bold]Reviewing {len(files)} file(s) with profile '{profile}'...[/]")

    review_profile = ReviewProfile(profile)
    bus = MessageBus()

    # Optional LLM provider
    llm = ClaudeCLIProvider() if use_llm else None

    # Instantiate agents (they auto-subscribe via the bus)
    SecurityAgent(bus, profile=review_profile, llm=llm)
    PerformanceAgent(bus, profile=review_profile, llm=llm)
    StyleAgent(bus, profile=review_profile, llm=llm)
    orchestrator = OrchestratorAgent(bus, profile=review_profile, llm=llm)

    request = ReviewRequest(
        files=files,
        profile=review_profile,
        use_llm=use_llm,
    )
    report = orchestrator.run_review(request)

    # Filter by minimum severity
    from src.models import Severity

    min_sev = Severity(min_severity)
    report.findings = [f for f in report.findings if f.severity.priority <= min_sev.priority]
    report._recompute_stats()

    if json_output:
        out = Console()
        out.print_json(json.dumps(report.model_dump(mode="json"), indent=2, default=str))
    else:
        render_report(report, Console())

    # Exit code: 1 if critical/high findings
    critical = report.findings_by_severity.get("critical", 0)
    high = report.findings_by_severity.get("high", 0)
    if critical or high:
        sys.exit(1)


if __name__ == "__main__":
    main()
