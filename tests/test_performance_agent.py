# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Tests for the PerformanceAgent."""

from __future__ import annotations

from src.agents.performance_agent import PerformanceAgent
from src.message_bus import MessageBus
from src.models import ReviewProfile
from tests.conftest import load_fixture, make_file_analysis


class TestPerformanceAgent:
    """PerformanceAgent detection tests."""

    def _agent(self, bus: MessageBus, profile: ReviewProfile = ReviewProfile.STANDARD) -> PerformanceAgent:
        return PerformanceAgent(bus, profile=profile)

    def test_detects_high_complexity(self, bus: MessageBus) -> None:
        """High-complexity function should be flagged."""
        agent = self._agent(bus)
        fa = load_fixture("sample_complex.py")
        findings = agent.analyze(fa)
        complexity_findings = [f for f in findings if f.category == "complexity"]
        assert len(complexity_findings) >= 1

    def test_detects_nested_loops(self, bus: MessageBus) -> None:
        """Nested for loops should be flagged."""
        agent = self._agent(bus)
        code = "def f(m):\n    for i in m:\n        for j in m:\n            pass\n"
        fa = make_file_analysis(code)
        findings = agent.analyze(fa)
        assert any(f.category == "nested_loop" for f in findings)

    def test_detects_mutable_default(self, bus: MessageBus) -> None:
        """Mutable default arguments should be flagged."""
        agent = self._agent(bus)
        code = "def f(items=[]):\n    items.append(1)\n    return items\n"
        fa = make_file_analysis(code)
        findings = agent.analyze(fa)
        assert any(f.category == "mutable_default" for f in findings)

    def test_detects_deep_nesting(self, bus: MessageBus) -> None:
        """Deeply nested code should be flagged."""
        agent = self._agent(bus, profile=ReviewProfile.THOROUGH)
        fa = load_fixture("sample_complex.py")
        findings = agent.analyze(fa)
        nesting_findings = [f for f in findings if f.category == "nesting"]
        assert len(nesting_findings) >= 1

    def test_detects_global_usage(self, bus: MessageBus) -> None:
        """global keyword should be flagged."""
        agent = self._agent(bus)
        code = "x = 0\ndef f():\n    global x\n    x += 1\n"
        fa = make_file_analysis(code)
        findings = agent.analyze(fa)
        assert any(f.category == "global_usage" for f in findings)

    def test_clean_code_minimal(self, bus: MessageBus) -> None:
        """Clean, short code should produce few or no performance findings."""
        agent = self._agent(bus)
        fa = load_fixture("sample_clean.py")
        findings = agent.analyze(fa)
        # Clean code should have at most info-level findings
        assert all(f.severity.priority >= 3 for f in findings)

    def test_star_import_thorough(self, bus: MessageBus) -> None:
        """Star imports should be flagged in thorough profile."""
        agent = self._agent(bus, profile=ReviewProfile.THOROUGH)
        code = "from os.path import *\ndef f():\n    return join('a', 'b')\n"
        fa = make_file_analysis(code)
        findings = agent.analyze(fa)
        assert any(f.category == "star_import" for f in findings)
