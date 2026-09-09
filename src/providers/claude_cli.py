# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Claude CLI provider -- calls `claude -p` via subprocess."""

from __future__ import annotations

import shutil
import subprocess
from typing import Optional

from src.providers.base import LLMProvider


class ClaudeCLIProvider(LLMProvider):
    """LLM provider that invokes the Claude CLI (`claude -p`).

    This is the default provider. It requires the Claude CLI to be
    installed and authenticated on the host machine. If unavailable,
    the system falls back to AST-only analysis.
    """

    def __init__(self, timeout_seconds: int = 60) -> None:
        self._timeout = timeout_seconds
        self._binary: Optional[str] = shutil.which("claude")

    def analyze(self, prompt: str, code: str) -> Optional[str]:
        """Analyze code via the Claude CLI.

        Args:
            prompt: Analysis instructions.
            code: Source code to review.

        Returns:
            Claude's response, or None on failure.
        """
        if not self.is_available():
            return None

        full_prompt = f"{prompt}\n\n```python\n{code}\n```"
        try:
            result = subprocess.run(
                [self._binary, "-p", full_prompt],  # type: ignore[arg-type]
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, OSError):
            return None

    def is_available(self) -> bool:
        """Check if the Claude CLI binary is on PATH."""
        return self._binary is not None

    @property
    def name(self) -> str:
        return "Claude CLI"
