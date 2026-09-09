# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Tests for the OrchestratorAgent end-to-end pipeline."""

from __future__ import annotations

from pathlib import Path

from src.agents.orchestrator import OrchestratorAgent
from src.agents.performance_agent import PerformanceAgent
from src.agents.security_agent import SecurityAgent
from src.agents.style_agent import StyleAgent
from src.message_bus import MessageBus
from src.models import ReviewProfile, ReviewRequest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestOrchestrator:
    """End-to-end orchestration tests."""

    def _setup_pipeline(
        self, bus: MessageBus, profile: ReviewProfile = ReviewProfile.STANDARD
    ) -> OrchestratorAgent:
        """Wire up all agents and return the orchestrator."""
        SecurityAgent(bus, profile=profile)
        PerformanceAgent(bus, profile=profile)
        StyleAgent(bus, profile=profile)
        return OrchestratorAgent(bus, profile=profile)

    def test_full_review_vulnerable(self, bus: MessageBus) -> None:
        """Full pipeline on vulnerable fixture should produce findings."""
        orch = self._setup_pipeline(bus)
        request = ReviewRequest(files=[str(FIXTURES_DIR / "sample_vulnerable.py")])
        report = orch.run_review(request)
        assert report.files_analyzed == 1
        assert report.total_findings > 0
        # Must include security findings
        assert report.findings_by_agent.get("security", 0) > 0

    def test_full_review_complex(self, bus: MessageBus) -> None:
        """Full pipeline on complex fixture should flag performance issues."""
        orch = self._setup_pipeline(bus, profile=ReviewProfile.THOROUGH)
        request = ReviewRequest(
            files=[str(FIXTURES_DIR / "sample_complex.py")],
            profile=ReviewProfile.THOROUGH,
        )
        report = orch.run_review(request)
        assert report.files_analyzed == 1
        assert report.findings_by_agent.get("performance", 0) > 0

    def test_full_review_clean(self, bus: MessageBus) -> None:
        """Clean code should produce fewer findings than vulnerable code."""
        bus_v = MessageBus()
        orch_v = self._setup_pipeline(bus_v)
        report_v = orch_v.run_review(
            ReviewRequest(files=[str(FIXTURES_DIR / "sample_vulnerable.py")])
        )

        bus_c = MessageBus()
        orch_c = self._setup_pipeline(bus_c)
        report_c = orch_c.run_review(
            ReviewRequest(files=[str(FIXTURES_DIR / "sample_clean.py")])
        )
        assert report_c.total_findings < report_v.total_findings

    def test_missing_file_skipped(self, bus: MessageBus) -> None:
        """Non-existent files should be silently skipped."""
        orch = self._setup_pipeline(bus)
        request = ReviewRequest(files=["nonexistent_file.py"])
        report = orch.run_review(request)
        assert report.files_analyzed == 0
        assert report.total_findings == 0

    def test_multiple_files(self, bus: MessageBus) -> None:
        """Review multiple files in one request."""
        orch = self._setup_pipeline(bus)
        request = ReviewRequest(
            files=[
                str(FIXTURES_DIR / "sample_vulnerable.py"),
                str(FIXTURES_DIR / "sample_clean.py"),
            ]
        )
        report = orch.run_review(request)
        assert report.files_analyzed == 2

    def test_report_duration(self, bus: MessageBus) -> None:
        """Report should have a non-negative duration."""
        orch = self._setup_pipeline(bus)
        request = ReviewRequest(files=[str(FIXTURES_DIR / "sample_clean.py")])
        report = orch.run_review(request)
        assert report.duration_seconds >= 0
