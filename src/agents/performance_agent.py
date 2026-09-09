# Multi-Agent Code Review System
# Author: Maharshi Soni | License: MIT
"""PerformanceAgent -- complexity analysis and bottleneck detection."""

from __future__ import annotations

import ast
from typing import Optional

from src.agents.base import BaseAgent
from src.message_bus import MessageBus
from src.models import AgentRole, FileAnalysis, Finding, ReviewProfile, Severity
from src.providers.base import LLMProvider

# Thresholds by profile
_COMPLEXITY_THRESHOLDS: dict[int, int] = {1: 15, 2: 10, 3: 7}
_NESTING_THRESHOLDS: dict[int, int] = {1: 5, 2: 4, 3: 3}
_FUNCTION_LENGTH_THRESHOLDS: dict[int, int] = {1: 80, 2: 50, 3: 30}
_PARAM_THRESHOLDS: dict[int, int] = {1: 8, 2: 6, 3: 5}


class PerformanceAgent(BaseAgent):
    """Analyzes code for performance issues and complexity.

    Checks for:
    - Cyclomatic complexity per function
    - Deep nesting levels
    - Overly long functions
    - Nested loops (quadratic/cubic patterns)
    - Global variable usage
    - Large parameter counts
    - Mutable default arguments
    """

    role = AgentRole.PERFORMANCE

    def __init__(
        self,
        bus: MessageBus,
        profile: ReviewProfile = ReviewProfile.STANDARD,
        llm: Optional[LLMProvider] = None,
    ) -> None:
        super().__init__(bus, profile, llm)

    def analyze(self, file_analysis: FileAnalysis) -> list[Finding]:
        """Run performance/complexity analysis."""
        findings: list[Finding] = []
        tree, errors = self.parse_ast(file_analysis.source_code)
        if tree is None:
            return findings

        for func in self.walk_functions(tree):
            findings.extend(self._check_complexity(func, file_analysis.file_path))
            findings.extend(self._check_nesting(func, file_analysis.file_path))
            findings.extend(self._check_function_length(func, file_analysis.file_path))
            findings.extend(self._check_nested_loops(func, file_analysis.file_path))

            if self.profile_depth >= 2:
                findings.extend(self._check_param_count(func, file_analysis.file_path))
                findings.extend(self._check_mutable_defaults(func, file_analysis.file_path))

        if self.profile_depth >= 2:
            findings.extend(self._check_global_usage(tree, file_analysis.file_path))

        if self.profile_depth >= 3:
            findings.extend(self._check_star_imports(tree, file_analysis.file_path))

        return findings

    # ------------------------------------------------------------------
    # Cyclomatic complexity (simplified)
    # ------------------------------------------------------------------

    def _check_complexity(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str
    ) -> list[Finding]:
        """Estimate cyclomatic complexity of a function."""
        complexity = 1  # base path
        for node in ast.walk(func):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                # each `and`/`or` adds a decision point
                complexity += len(node.values) - 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.Assert, ast.IfExp)):
                complexity += 1

        threshold = _COMPLEXITY_THRESHOLDS[self.profile_depth]
        if complexity > threshold:
            severity = Severity.HIGH if complexity > threshold * 2 else Severity.MEDIUM
            return [
                Finding(
                    agent=self.role,
                    severity=severity,
                    title=f"High complexity: {func.name}() = {complexity}",
                    description=(
                        f"Function '{func.name}' has cyclomatic complexity {complexity} "
                        f"(threshold: {threshold}). Consider refactoring."
                    ),
                    file_path=file_path,
                    line_number=func.lineno,
                    category="complexity",
                    suggestion="Break this function into smaller helpers.",
                )
            ]
        return []

    # ------------------------------------------------------------------
    # Nesting depth
    # ------------------------------------------------------------------

    def _check_nesting(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str
    ) -> list[Finding]:
        """Measure maximum nesting depth."""
        max_depth = self._max_depth(func.body, 0)
        threshold = _NESTING_THRESHOLDS[self.profile_depth]
        if max_depth > threshold:
            return [
                Finding(
                    agent=self.role,
                    severity=Severity.MEDIUM,
                    title=f"Deep nesting: {func.name}() depth={max_depth}",
                    description=(
                        f"Function '{func.name}' has nesting depth {max_depth} "
                        f"(threshold: {threshold}). Deeply nested code is hard to follow."
                    ),
                    file_path=file_path,
                    line_number=func.lineno,
                    category="nesting",
                    suggestion="Use early returns or extract inner blocks to helpers.",
                )
            ]
        return []

    def _max_depth(self, body: list[ast.stmt], current: int) -> int:
        """Recursively compute the maximum nesting depth."""
        deepest = current
        for node in body:
            if isinstance(node, (ast.If, ast.For, ast.While, ast.AsyncFor, ast.With, ast.AsyncWith)):
                child_bodies: list[list[ast.stmt]] = []
                if hasattr(node, "body"):
                    child_bodies.append(node.body)
                if hasattr(node, "orelse") and node.orelse:
                    child_bodies.append(node.orelse)
                for child_body in child_bodies:
                    deepest = max(deepest, self._max_depth(child_body, current + 1))
            elif isinstance(node, ast.Try):
                for child_body in [node.body, node.orelse, node.finalbody]:
                    if child_body:
                        deepest = max(deepest, self._max_depth(child_body, current + 1))
                for handler in node.handlers:
                    deepest = max(deepest, self._max_depth(handler.body, current + 1))
        return deepest

    # ------------------------------------------------------------------
    # Function length
    # ------------------------------------------------------------------

    def _check_function_length(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str
    ) -> list[Finding]:
        """Flag overly long functions."""
        if func.end_lineno is None:
            return []
        length = func.end_lineno - func.lineno + 1
        threshold = _FUNCTION_LENGTH_THRESHOLDS[self.profile_depth]
        if length > threshold:
            return [
                Finding(
                    agent=self.role,
                    severity=Severity.LOW,
                    title=f"Long function: {func.name}() ({length} lines)",
                    description=(
                        f"Function '{func.name}' is {length} lines long "
                        f"(threshold: {threshold})."
                    ),
                    file_path=file_path,
                    line_number=func.lineno,
                    end_line=func.end_lineno,
                    category="function_length",
                    suggestion="Extract logical sections into helper functions.",
                )
            ]
        return []

    # ------------------------------------------------------------------
    # Nested loops
    # ------------------------------------------------------------------

    def _check_nested_loops(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str
    ) -> list[Finding]:
        """Detect nested for/while loops (potential O(n^2+))."""
        findings: list[Finding] = []
        for node in ast.walk(func):
            if isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
                for inner in ast.walk(node):
                    if inner is not node and isinstance(
                        inner, (ast.For, ast.While, ast.AsyncFor)
                    ):
                        findings.append(
                            Finding(
                                agent=self.role,
                                severity=Severity.MEDIUM,
                                title=f"Nested loop in {func.name}()",
                                description=(
                                    "Nested loops can indicate O(n^2) or worse complexity. "
                                    "Review whether the inner loop is necessary."
                                ),
                                file_path=file_path,
                                line_number=inner.lineno,
                                category="nested_loop",
                                suggestion="Consider using sets, dicts, or itertools to flatten.",
                            )
                        )
                        # Only flag once per outer loop
                        break
        return findings

    # ------------------------------------------------------------------
    # Parameter count
    # ------------------------------------------------------------------

    def _check_param_count(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str
    ) -> list[Finding]:
        """Flag functions with too many parameters."""
        args = func.args
        count = (
            len(args.args)
            + len(args.posonlyargs)
            + len(args.kwonlyargs)
        )
        # Subtract 'self'/'cls'
        if count > 0 and args.args and args.args[0].arg in ("self", "cls"):
            count -= 1
        threshold = _PARAM_THRESHOLDS[self.profile_depth]
        if count > threshold:
            return [
                Finding(
                    agent=self.role,
                    severity=Severity.LOW,
                    title=f"Too many params: {func.name}() has {count}",
                    description=(
                        f"Function '{func.name}' takes {count} parameters "
                        f"(threshold: {threshold}). This hinders readability."
                    ),
                    file_path=file_path,
                    line_number=func.lineno,
                    category="param_count",
                    suggestion="Group related params into a dataclass or config object.",
                )
            ]
        return []

    # ------------------------------------------------------------------
    # Mutable default arguments
    # ------------------------------------------------------------------

    def _check_mutable_defaults(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str
    ) -> list[Finding]:
        """Detect mutable default argument values."""
        findings: list[Finding] = []
        for default in func.args.defaults + func.args.kw_defaults:
            if default is not None and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                findings.append(
                    Finding(
                        agent=self.role,
                        severity=Severity.MEDIUM,
                        title=f"Mutable default in {func.name}()",
                        description=(
                            "Mutable default arguments are shared across calls. "
                            "This is a common source of bugs."
                        ),
                        file_path=file_path,
                        line_number=func.lineno,
                        category="mutable_default",
                        suggestion="Use None as default and create the mutable inside the body.",
                    )
                )
                break  # one finding per function
        return findings

    # ------------------------------------------------------------------
    # Global usage
    # ------------------------------------------------------------------

    def _check_global_usage(self, tree: ast.Module, file_path: str) -> list[Finding]:
        """Flag usage of the `global` keyword."""
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                findings.append(
                    Finding(
                        agent=self.role,
                        severity=Severity.LOW,
                        title=f"Global variable: {', '.join(node.names)}",
                        description=(
                            "Global mutable state makes code harder to test and reason about."
                        ),
                        file_path=file_path,
                        line_number=node.lineno,
                        category="global_usage",
                        suggestion="Pass state explicitly or use a class.",
                    )
                )
        return findings

    # ------------------------------------------------------------------
    # Star imports
    # ------------------------------------------------------------------

    def _check_star_imports(self, tree: ast.Module, file_path: str) -> list[Finding]:
        """Flag wildcard imports."""
        findings: list[Finding] = []
        for imp in self.walk_imports(tree):
            if isinstance(imp, ast.ImportFrom):
                for alias in imp.names:
                    if alias.name == "*":
                        findings.append(
                            Finding(
                                agent=self.role,
                                severity=Severity.LOW,
                                title=f"Star import from {imp.module}",
                                description=(
                                    "Wildcard imports pollute the namespace and make it "
                                    "unclear where names come from."
                                ),
                                file_path=file_path,
                                line_number=imp.lineno,
                                category="star_import",
                                suggestion="Import specific names instead.",
                            )
                        )
        return findings
