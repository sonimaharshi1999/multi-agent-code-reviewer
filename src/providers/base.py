# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """Abstract LLM provider interface.

    All LLM providers must implement the `analyze` method.
    The LLM layer is optional -- core AST analysis works without it.
    """

    @abstractmethod
    def analyze(self, prompt: str, code: str) -> Optional[str]:
        """Send code to an LLM for enhanced analysis.

        Args:
            prompt: The analysis prompt describing what to look for.
            code: The source code to analyze.

        Returns:
            LLM response text, or None if the provider is unavailable.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether this provider is configured and reachable."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...
