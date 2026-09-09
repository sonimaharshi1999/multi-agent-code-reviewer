# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Tests for the StyleAgent."""

from __future__ import annotations

from src.agents.style_agent import StyleAgent
from src.message_bus import MessageBus
from src.models import ReviewProfile
from tests.conftest import load_fixture, make_file_analysis


class TestStyleAgent:
    """StyleAgent detection tests."""

    def _agent(self, bus: MessageBus, profile: ReviewProfile = ReviewProfile.STANDARD) -> StyleAgent:
        return StyleAgent(bus, profile=profile)

    def test_detects_missing_docstring(self, bus: MessageBus) -> None:
        """Public function without docstring should be flagged."""
        agent = self._agent(bus)
        code = "def public_func(x):\n    return x + 1\n"
        fa = make_file_analysis(code)
        findings = agent.analyze(fa)
        assert any(f.category == "missing_docstring" for f in findings)

    def test_detects_bad_function_name(self, bus: MessageBus) -> None:
        """CamelCase function names should be flagged."""
        agent = self._agent(bus)
        code = 'def MyFunc():\n    """Docs."""\n    return 1\n'
        fa = make_file_analysis(code)
        findings = agent.analyze(fa)
        assert any(f.category == "naming" for f in findings)

    def test_detects_bad_class_name(self, bus: MessageBus) -> None:
        """lowercase class names should be flagged."""
        agent = self._agent(bus)
        code = 'class my_class:\n    """Docs."""\n    pass\n'
        fa = make_file_analysis(code)
        findings = agent.analyze(fa)
        assert any(f.category == "naming" and "class" in f.title.lower() for f in findings)

    def test_detects_bare_except(self, bus: MessageBus) -> None:
        """Bare except clauses should be flagged."""
        agent = self._agent(bus)
        code = "def f():\n    try:\n        pass\n    except:\n        pass\n"
        fa = make_file_analysis(code)
        findings = agent.analyze(fa)
        assert any(f.category == "bare_except" for f in findings)

    def test_detects_todo_comments(self, bus: MessageBus) -> None:
        """TODO comments should be surfaced."""
        agent = self._agent(bus)
        code = "# TODO: fix this\ndef f():\n    '''D.'''\n    pass\n"
        fa = make_file_analysis(code)
        findings = agent.analyze(fa)
        assert any(f.category == "todo_comment" for f in findings)

    def test_fixture_style_issues(self, bus: MessageBus) -> None:
        """The style-issues fixture should produce many findings."""
        agent = self._agent(bus, profile=ReviewProfile.THOROUGH)
        fa = load_fixture("sample_style_issues.py")
        findings = agent.analyze(fa)
        categories = {f.category for f in findings}
        assert "missing_docstring" in categories
        assert "naming" in categories

    def test_clean_code_minimal_findings(self, bus: MessageBus) -> None:
        """Clean code should produce few style findings."""
        agent = self._agent(bus)
        fa = load_fixture("sample_clean.py")
        findings = agent.analyze(fa)
        # The clean fixture follows conventions; expect very few findings
        assert len(findings) <= 3
