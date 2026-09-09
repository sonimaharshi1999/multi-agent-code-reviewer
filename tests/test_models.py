# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Tests for Pydantic models."""

from __future__ import annotations

from src.models import (
    AgentRole,
    Finding,
    ReviewReport,
    ReviewRequest,
    ReviewProfile,
    Severity,
)


class TestSeverity:
    """Severity enum tests."""

    def test_priority_ordering(self) -> None:
        """Critical should have the lowest (most urgent) priority number."""
        assert Severity.CRITICAL.priority < Severity.HIGH.priority
        assert Severity.HIGH.priority < Severity.MEDIUM.priority
        assert Severity.MEDIUM.priority < Severity.LOW.priority
        assert Severity.LOW.priority < Severity.INFO.priority

    def test_all_severities_have_priority(self) -> None:
        """Every severity value must map to a priority."""
        for sev in Severity:
            assert isinstance(sev.priority, int)


class TestFinding:
    """Finding model tests."""

    def test_fingerprint_uniqueness(self) -> None:
        """Different findings should produce different fingerprints."""
        f1 = Finding(
            agent=AgentRole.SECURITY,
            severity=Severity.HIGH,
            title="eval() call",
            description="desc",
            file_path="a.py",
            line_number=10,
            category="dangerous_call",
        )
        f2 = Finding(
            agent=AgentRole.SECURITY,
            severity=Severity.HIGH,
            title="exec() call",
            description="desc",
            file_path="a.py",
            line_number=20,
            category="dangerous_call",
        )
        assert f1.fingerprint() != f2.fingerprint()

    def test_fingerprint_deterministic(self) -> None:
        """Same inputs produce the same fingerprint."""
        kwargs = dict(
            agent=AgentRole.STYLE,
            severity=Severity.LOW,
            title="test",
            description="d",
            file_path="b.py",
            line_number=5,
            category="naming",
        )
        f1 = Finding(**kwargs)
        f2 = Finding(**kwargs)
        assert f1.fingerprint() == f2.fingerprint()


class TestReviewReport:
    """ReviewReport aggregation tests."""

    def _make_finding(self, agent: AgentRole, severity: Severity, line: int) -> Finding:
        return Finding(
            agent=agent,
            severity=severity,
            title=f"test-{line}",
            description="d",
            file_path="x.py",
            line_number=line,
            category="cat",
        )

    def test_add_findings_deduplication(self) -> None:
        """Duplicate findings should not appear twice."""
        report = ReviewReport(request=ReviewRequest(files=["x.py"]))
        f = self._make_finding(AgentRole.SECURITY, Severity.HIGH, 1)
        report.add_findings([f, f])
        assert report.total_findings == 1

    def test_sorted_findings_order(self) -> None:
        """sorted_findings should return critical before low."""
        report = ReviewReport(request=ReviewRequest(files=["x.py"]))
        low = self._make_finding(AgentRole.STYLE, Severity.LOW, 100)
        crit = self._make_finding(AgentRole.SECURITY, Severity.CRITICAL, 1)
        report.add_findings([low, crit])
        ordered = report.sorted_findings()
        assert ordered[0].severity == Severity.CRITICAL
        assert ordered[1].severity == Severity.LOW

    def test_stats_recomputed(self) -> None:
        """Stats should update after add_findings."""
        report = ReviewReport(request=ReviewRequest(files=["x.py"]))
        report.add_findings([
            self._make_finding(AgentRole.SECURITY, Severity.HIGH, 1),
            self._make_finding(AgentRole.PERFORMANCE, Severity.MEDIUM, 2),
        ])
        assert report.findings_by_severity["high"] == 1
        assert report.findings_by_severity["medium"] == 1
        assert report.findings_by_agent["security"] == 1
        assert report.findings_by_agent["performance"] == 1
