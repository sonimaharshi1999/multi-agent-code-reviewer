# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""Pydantic models for the multi-agent code review system."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def priority(self) -> int:
        """Numeric priority for sorting (lower = more severe)."""
        return {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }[self]


class AgentRole(str, Enum):
    """Roles for specialized review agents."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    ORCHESTRATOR = "orchestrator"


class ReviewProfile(str, Enum):
    """Configurable review depth profiles."""

    QUICK = "quick"
    STANDARD = "standard"
    THOROUGH = "thorough"


class Finding(BaseModel):
    """A single code review finding from an agent."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    agent: AgentRole
    severity: Severity
    title: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    end_line: Optional[int] = None
    suggestion: Optional[str] = None
    category: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)

    def fingerprint(self) -> str:
        """Generate a deduplication fingerprint."""
        return f"{self.agent}:{self.category}:{self.file_path}:{self.line_number}:{self.title}"


class Message(BaseModel):
    """Message passed between agents via the message bus."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    sender: AgentRole
    recipient: Optional[AgentRole] = None  # None = broadcast
    msg_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class FileAnalysis(BaseModel):
    """Analysis context for a single file."""

    file_path: str
    source_code: str
    line_count: int = 0
    ast_valid: bool = False
    ast_errors: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    """A request to review one or more files."""

    files: list[str]
    profile: ReviewProfile = ReviewProfile.STANDARD
    use_llm: bool = False
    llm_provider: str = "claude_cli"


class ReviewReport(BaseModel):
    """Complete review report aggregating all agent findings."""

    request: ReviewRequest
    files_analyzed: int = 0
    total_findings: int = 0
    findings_by_severity: dict[str, int] = Field(default_factory=dict)
    findings_by_agent: dict[str, int] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    duration_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)

    def add_findings(self, new_findings: list[Finding]) -> None:
        """Add findings with deduplication."""
        existing_fps: set[str] = {f.fingerprint() for f in self.findings}
        for finding in new_findings:
            fp = finding.fingerprint()
            if fp not in existing_fps:
                self.findings.append(finding)
                existing_fps.add(fp)
        self._recompute_stats()

    def _recompute_stats(self) -> None:
        """Recompute aggregate statistics."""
        self.total_findings = len(self.findings)
        self.findings_by_severity = {}
        self.findings_by_agent = {}
        for f in self.findings:
            sev = f.severity.value
            self.findings_by_severity[sev] = self.findings_by_severity.get(sev, 0) + 1
            agent = f.agent.value
            self.findings_by_agent[agent] = self.findings_by_agent.get(agent, 0) + 1

    def sorted_findings(self) -> list[Finding]:
        """Return findings sorted by severity priority then line number."""
        return sorted(
            self.findings,
            key=lambda f: (f.severity.priority, f.file_path, f.line_number or 0),
        )
