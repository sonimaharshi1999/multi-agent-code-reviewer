# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Tests for LLM provider abstractions."""

from __future__ import annotations

from src.providers.api_provider import APIProvider
from src.providers.claude_cli import ClaudeCLIProvider


class TestClaudeCLIProvider:
    """ClaudeCLIProvider tests."""

    def test_name(self) -> None:
        """Provider should identify itself."""
        p = ClaudeCLIProvider()
        assert p.name == "Claude CLI"

    def test_analyze_returns_none_when_unavailable(self) -> None:
        """If binary is missing, analyze should return None gracefully."""
        p = ClaudeCLIProvider()
        # Force unavailable
        p._binary = None
        result = p.analyze("test prompt", "print(1)")
        assert result is None


class TestAPIProvider:
    """APIProvider tests."""

    def test_unavailable_by_default(self) -> None:
        """With no config, provider should be unavailable."""
        p = APIProvider()
        assert p.is_available() is False

    def test_available_when_configured(self) -> None:
        """Provider should report available when both url and key set."""
        p = APIProvider(base_url="https://example.com", api_key="key")
        assert p.is_available() is True

    def test_name_includes_model(self) -> None:
        """Name should include the model identifier."""
        p = APIProvider(model="gpt-4")
        assert "gpt-4" in p.name

    def test_analyze_stub_returns_none(self) -> None:
        """Stub implementation should return None even when available."""
        p = APIProvider(base_url="https://example.com", api_key="key")
        result = p.analyze("prompt", "code")
        assert result is None
