# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""OrchestratorAgent -- coordinates reviews and merges findings."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from src.message_bus import MessageBus
from src.models import (
    AgentRole,
    FileAnalysis,
    Finding,
    Message,
    ReviewProfile,
    ReviewReport,
    ReviewRequest,
)
from src.providers.base import LLMProvider


class OrchestratorAgent:
    """Coordinates the review pipeline.

    Responsibilities:
    - Reads source files and parses them into FileAnalysis objects
    - Dispatches review_file messages to specialized agents
    - Collects findings from all agents
    - Deduplicates and priority-sorts the final report
    """

    role = AgentRole.ORCHESTRATOR

    def __init__(
        self,
        bus: MessageBus,
        profile: ReviewProfile = ReviewProfile.STANDARD,
        llm: Optional[LLMProvider] = None,
    ) -> None:
        self._bus = bus
        self._profile = profile
        self._llm = llm
        self._collected_findings: list[Finding] = []
        self._bus.subscribe("findings", self._on_findings, agent_role=self.role)

    def _on_findings(self, message: Message) -> None:
        """Collect findings from specialized agents."""
        raw_findings = message.payload.get("findings", [])
        for raw in raw_findings:
            self._collected_findings.append(Finding(**raw))

    def run_review(self, request: ReviewRequest) -> ReviewReport:
        """Execute a full review cycle.

        Args:
            request: The review request with file paths and settings.

        Returns:
            Aggregated review report.
        """
        start = time.monotonic()
        report = ReviewReport(request=request)
        self._collected_findings.clear()

        for file_path in request.files:
            file_analysis = self._load_file(file_path)
            if file_analysis is None:
                continue
            report.files_analyzed += 1
            self._dispatch_review(file_analysis)

        report.add_findings(self._collected_findings)
        report.duration_seconds = round(time.monotonic() - start, 3)
        return report

    def _load_file(self, file_path: str) -> Optional[FileAnalysis]:
        """Read a file and produce a FileAnalysis."""
        path = Path(file_path)
        if not path.exists():
            return None
        if not path.suffix == ".py":
            return None
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        lines = source.splitlines()
        return FileAnalysis(
            file_path=str(path.resolve()),
            source_code=source,
            line_count=len(lines),
            ast_valid=True,
        )

    def _load_source(self, source: str, label: str = "<source>") -> FileAnalysis:
        """Create a FileAnalysis from a raw source string (for testing)."""
        lines = source.splitlines()
        return FileAnalysis(
            file_path=label,
            source_code=source,
            line_count=len(lines),
            ast_valid=True,
        )

    def _dispatch_review(self, file_analysis: FileAnalysis) -> None:
        """Send a review_file message so all agents pick it up."""
        self._bus.publish(
            Message(
                sender=self.role,
                recipient=None,  # broadcast
                msg_type="review_file",
                payload={"file_analysis": file_analysis.model_dump(mode="json")},
            )
        )
