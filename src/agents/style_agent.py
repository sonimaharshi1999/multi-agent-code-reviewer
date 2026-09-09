# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""StyleAgent -- code quality, conventions, and documentation checks."""

from __future__ import annotations

import ast
import re
from typing import Optional

from src.agents.base import BaseAgent
from src.message_bus import MessageBus
from src.models import AgentRole, FileAnalysis, Finding, ReviewProfile, Severity
from src.providers.base import LLMProvider

_SNAKE_RE = re.compile(r"^_?_?[a-z][a-z0-9_]*_?_?$")
_UPPER_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_PASCAL_RE = re.compile(r"^_?[A-Z][a-zA-Z0-9]*$")

_LINE_LENGTH_THRESHOLDS: dict[int, int] = {1: 120, 2: 100, 3: 88}


class StyleAgent(BaseAgent):
    """Checks code quality, naming conventions, and documentation.

    Checks for:
    - Missing docstrings on public functions/classes
    - Missing type hints
    - Naming convention violations (PEP 8)
    - Line length
    - Bare except clauses
    - TODO/FIXME/HACK comments
    - Unused imports (basic heuristic)
    """

    role = AgentRole.STYLE

    def __init__(
        self,
        bus: MessageBus,
        profile: ReviewProfile = ReviewProfile.STANDARD,
        llm: Optional[LLMProvider] = None,
    ) -> None:
        super().__init__(bus, profile, llm)

    def analyze(self, file_analysis: FileAnalysis) -> list[Finding]:
        """Run style and documentation analysis."""
        findings: list[Finding] = []
        tree, errors = self.parse_ast(file_analysis.source_code)
        if tree is None:
            return findings

        findings.extend(self._check_docstrings(tree, file_analysis.file_path))
        findings.extend(self._check_naming(tree, file_analysis.file_path))
        findings.extend(self._check_bare_except(tree, file_analysis.file_path))

        if self.profile_depth >= 2:
            findings.extend(
                self._check_type_hints(tree, file_analysis.file_path)
            )
            findings.extend(
                self._check_line_length(file_analysis.source_code, file_analysis.file_path)
            )
            findings.extend(
                self._check_todo_comments(file_analysis.source_code, file_analysis.file_path)
            )

        if self.profile_depth >= 3:
            findings.extend(
                self._check_unused_imports(tree, file_analysis.source_code, file_analysis.file_path)
            )

        return findings

    # ------------------------------------------------------------------
    # Docstrings
    # ------------------------------------------------------------------

    def _check_docstrings(self, tree: ast.Module, file_path: str) -> list[Finding]:
        """Flag public functions and classes missing docstrings."""
        findings: list[Finding] = []
        for func in self.walk_functions(tree):
            if func.name.startswith("_"):
                continue
            if not ast.get_docstring(func):
                findings.append(
                    Finding(
                        agent=self.role,
                        severity=Severity.LOW,
                        title=f"Missing docstring: {func.name}()",
                        description=(
                            f"Public function '{func.name}' has no docstring."
                        ),
                        file_path=file_path,
                        line_number=func.lineno,
                        category="missing_docstring",
                        suggestion="Add a docstring describing purpose, args, and return value.",
                    )
                )
        for cls in self.walk_classes(tree):
            if cls.name.startswith("_"):
                continue
            if not ast.get_docstring(cls):
                findings.append(
                    Finding(
                        agent=self.role,
                        severity=Severity.LOW,
                        title=f"Missing docstring: class {cls.name}",
                        description=f"Public class '{cls.name}' has no docstring.",
                        file_path=file_path,
                        line_number=cls.lineno,
                        category="missing_docstring",
                        suggestion="Add a class-level docstring.",
                    )
                )
        return findings

    # ------------------------------------------------------------------
    # Naming conventions
    # ------------------------------------------------------------------

    def _check_naming(self, tree: ast.Module, file_path: str) -> list[Finding]:
        """Check PEP 8 naming conventions."""
        findings: list[Finding] = []

        # Functions should be snake_case
        for func in self.walk_functions(tree):
            if not _SNAKE_RE.match(func.name):
                findings.append(
                    Finding(
                        agent=self.role,
                        severity=Severity.LOW,
                        title=f"Non-snake_case function: {func.name}",
                        description=(
                            f"Function '{func.name}' does not follow snake_case convention."
                        ),
                        file_path=file_path,
                        line_number=func.lineno,
                        category="naming",
                        suggestion="Rename to snake_case per PEP 8.",
                    )
                )

        # Classes should be PascalCase
        for cls in self.walk_classes(tree):
            if not _PASCAL_RE.match(cls.name):
                findings.append(
                    Finding(
                        agent=self.role,
                        severity=Severity.LOW,
                        title=f"Non-PascalCase class: {cls.name}",
                        description=(
                            f"Class '{cls.name}' does not follow PascalCase convention."
                        ),
                        file_path=file_path,
                        line_number=cls.lineno,
                        category="naming",
                        suggestion="Rename to PascalCase per PEP 8.",
                    )
                )

        return findings

    # ------------------------------------------------------------------
    # Type hints
    # ------------------------------------------------------------------

    def _check_type_hints(self, tree: ast.Module, file_path: str) -> list[Finding]:
        """Flag public functions missing return type annotations."""
        findings: list[Finding] = []
        for func in self.walk_functions(tree):
            if func.name.startswith("_"):
                continue
            if func.returns is None:
                findings.append(
                    Finding(
                        agent=self.role,
                        severity=Severity.INFO,
                        title=f"Missing return type: {func.name}()",
                        description=(
                            f"Function '{func.name}' has no return type annotation."
                        ),
                        file_path=file_path,
                        line_number=func.lineno,
                        category="type_hint",
                        suggestion="Add a return type annotation (e.g. -> None, -> str).",
                    )
                )
        return findings

    # ------------------------------------------------------------------
    # Bare except
    # ------------------------------------------------------------------

    def _check_bare_except(self, tree: ast.Module, file_path: str) -> list[Finding]:
        """Flag bare except clauses."""
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                findings.append(
                    Finding(
                        agent=self.role,
                        severity=Severity.MEDIUM,
                        title="Bare except clause",
                        description=(
                            "Bare `except:` catches all exceptions including "
                            "KeyboardInterrupt and SystemExit."
                        ),
                        file_path=file_path,
                        line_number=node.lineno,
                        category="bare_except",
                        suggestion="Catch a specific exception type, e.g. `except Exception:`.",
                    )
                )
        return findings

    # ------------------------------------------------------------------
    # Line length
    # ------------------------------------------------------------------

    def _check_line_length(self, source: str, file_path: str) -> list[Finding]:
        """Flag lines exceeding the threshold."""
        findings: list[Finding] = []
        threshold = _LINE_LENGTH_THRESHOLDS[self.profile_depth]
        max_reports = 5  # limit noise
        count = 0
        for i, line in enumerate(source.splitlines(), start=1):
            if len(line) > threshold:
                count += 1
                if count <= max_reports:
                    findings.append(
                        Finding(
                            agent=self.role,
                            severity=Severity.INFO,
                            title=f"Line too long ({len(line)} > {threshold})",
                            description=f"Line {i} is {len(line)} characters.",
                            file_path=file_path,
                            line_number=i,
                            category="line_length",
                            suggestion=f"Keep lines under {threshold} characters.",
                        )
                    )
        if count > max_reports:
            findings.append(
                Finding(
                    agent=self.role,
                    severity=Severity.INFO,
                    title=f"{count - max_reports} more long lines",
                    description=f"Total of {count} lines exceed {threshold} characters.",
                    file_path=file_path,
                    category="line_length",
                )
            )
        return findings

    # ------------------------------------------------------------------
    # TODO / FIXME / HACK comments
    # ------------------------------------------------------------------

    def _check_todo_comments(self, source: str, file_path: str) -> list[Finding]:
        """Surface TODO, FIXME, and HACK comments."""
        findings: list[Finding] = []
        pattern = re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
        for i, line in enumerate(source.splitlines(), start=1):
            match = pattern.search(line)
            if match:
                tag = match.group(1).upper()
                findings.append(
                    Finding(
                        agent=self.role,
                        severity=Severity.INFO,
                        title=f"{tag} comment on line {i}",
                        description=line.strip(),
                        file_path=file_path,
                        line_number=i,
                        category="todo_comment",
                    )
                )
        return findings

    # ------------------------------------------------------------------
    # Unused imports (heuristic)
    # ------------------------------------------------------------------

    def _check_unused_imports(
        self, tree: ast.Module, source: str, file_path: str
    ) -> list[Finding]:
        """Basic heuristic: flag imported names not referenced elsewhere in source."""
        findings: list[Finding] = []
        for imp in self.walk_imports(tree):
            if isinstance(imp, ast.Import):
                for alias in imp.names:
                    used_name = alias.asname or alias.name.split(".")[0]
                    if self._count_occurrences(used_name, source) <= 1:
                        findings.append(
                            Finding(
                                agent=self.role,
                                severity=Severity.INFO,
                                title=f"Possibly unused import: {alias.name}",
                                description=f"'{used_name}' appears only in the import statement.",
                                file_path=file_path,
                                line_number=imp.lineno,
                                category="unused_import",
                                suggestion="Remove if unused.",
                            )
                        )
            elif isinstance(imp, ast.ImportFrom):
                for alias in imp.names:
                    if alias.name == "*":
                        continue
                    used_name = alias.asname or alias.name
                    if self._count_occurrences(used_name, source) <= 1:
                        findings.append(
                            Finding(
                                agent=self.role,
                                severity=Severity.INFO,
                                title=f"Possibly unused import: {alias.name}",
                                description=f"'{used_name}' appears only in the import statement.",
                                file_path=file_path,
                                line_number=imp.lineno,
                                category="unused_import",
                                suggestion="Remove if unused.",
                            )
                        )
        return findings

    @staticmethod
    def _count_occurrences(name: str, source: str) -> int:
        """Count word-boundary occurrences of a name in source."""
        pattern = re.compile(rf"\b{re.escape(name)}\b")
        return len(pattern.findall(source))
