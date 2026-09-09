# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Tests for the SecurityAgent."""

from __future__ import annotations

from src.agents.security_agent import SecurityAgent
from src.message_bus import MessageBus
from src.models import ReviewProfile, Severity
from tests.conftest import load_fixture, make_file_analysis


class TestSecurityAgent:
    """SecurityAgent detection tests."""

    def _agent(self, bus: MessageBus, profile: ReviewProfile = ReviewProfile.STANDARD) -> SecurityAgent:
        return SecurityAgent(bus, profile=profile)

    def test_detects_eval(self, bus: MessageBus) -> None:
        """eval() should be flagged as CRITICAL."""
        agent = self._agent(bus)
        fa = make_file_analysis("x = eval(input())\n")
        findings = agent.analyze(fa)
        assert any(f.title.startswith("Dangerous call: eval") for f in findings)
        assert any(f.severity == Severity.CRITICAL for f in findings)

    def test_detects_exec(self, bus: MessageBus) -> None:
        """exec() should be flagged as CRITICAL."""
        agent = self._agent(bus)
        fa = make_file_analysis("exec('print(1)')\n")
        findings = agent.analyze(fa)
        assert any("exec" in f.title for f in findings)

    def test_detects_os_system(self, bus: MessageBus) -> None:
        """os.system() should be flagged."""
        agent = self._agent(bus)
        fa = make_file_analysis("import os\nos.system('ls')\n")
        findings = agent.analyze(fa)
        assert any("os.system" in f.title for f in findings)

    def test_detects_hardcoded_secret(self, bus: MessageBus) -> None:
        """Hardcoded API_KEY should be flagged."""
        agent = self._agent(bus)
        fa = make_file_analysis('API_KEY = "sk-12345"\n')
        findings = agent.analyze(fa)
        assert any(f.category == "hardcoded_secret" for f in findings)

    def test_detects_sql_injection(self, bus: MessageBus) -> None:
        """f-string SQL query construction should be flagged."""
        agent = self._agent(bus)
        code = 'query = f"SELECT * FROM users WHERE id = {uid}"\n'
        fa = make_file_analysis(code)
        findings = agent.analyze(fa)
        assert any(f.category == "sql_injection" for f in findings)

    def test_shell_true(self, bus: MessageBus) -> None:
        """subprocess with shell=True should be flagged."""
        agent = self._agent(bus)
        code = "import subprocess\nsubprocess.run('ls', shell=True)\n"
        fa = make_file_analysis(code)
        findings = agent.analyze(fa)
        assert any(f.category == "shell_injection" for f in findings)

    def test_clean_code_no_critical(self, bus: MessageBus) -> None:
        """Clean code should produce no critical/high findings."""
        agent = self._agent(bus)
        fa = load_fixture("sample_clean.py")
        findings = agent.analyze(fa)
        assert all(f.severity not in (Severity.CRITICAL, Severity.HIGH) for f in findings)

    def test_fixture_vulnerable_finds_multiple(self, bus: MessageBus) -> None:
        """The vulnerable fixture should produce many findings."""
        agent = self._agent(bus, profile=ReviewProfile.THOROUGH)
        fa = load_fixture("sample_vulnerable.py")
        findings = agent.analyze(fa)
        # Should find eval, exec, os.system, hardcoded secrets, SQL injection, etc.
        assert len(findings) >= 5
