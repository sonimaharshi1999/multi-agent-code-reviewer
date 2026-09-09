# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Generic API provider stub -- user configures endpoint and key."""

from __future__ import annotations

from typing import Optional

from src.providers.base import LLMProvider


class APIProvider(LLMProvider):
    """Placeholder API provider for user-configured LLM endpoints.

    Users can subclass this or supply ``base_url`` and ``api_key``
    to integrate any OpenAI-compatible API. This stub always reports
    itself as unavailable unless explicitly configured.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "default",
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model

    def analyze(self, prompt: str, code: str) -> Optional[str]:
        """Analyze code via a remote API.

        Not implemented in this stub -- returns None.
        Subclass and override for real integrations.
        """
        if not self.is_available():
            return None
        # Placeholder: real implementation would POST to self._base_url
        return None

    def is_available(self) -> bool:
        """Available only when both base_url and api_key are set."""
        return bool(self._base_url and self._api_key)

    @property
    def name(self) -> str:
        return f"API ({self._model})"
